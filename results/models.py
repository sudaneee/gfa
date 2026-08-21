from django.conf import settings
from django.db import models


class GradeBoundary(models.Model):
    """Configurable grade bands — admin-editable, matches the frontend prototype's A–F system."""

    grade = models.CharField(max_length=2, unique=True)
    min_score = models.PositiveSmallIntegerField()
    max_score = models.PositiveSmallIntegerField()
    point = models.PositiveSmallIntegerField(default=0)
    remark = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['-min_score']

    def __str__(self):
        return f"{self.grade} ({self.min_score}–{self.max_score})"

    @classmethod
    def for_score(cls, total):
        return cls.objects.filter(min_score__lte=total, max_score__gte=total).first()


class ScoreComponent(models.Model):
    """A configurable continuous-assessment column (CA1, CA2, CA3, ...).
    Global and admin-managed rather than per-subject/per-school — this is a
    single-school app and nothing asks for Maths to have a different CA
    breakdown than English, just for the breakdown itself to be editable
    without a code change."""

    name = models.CharField(max_length=30, unique=True)
    max_score = models.PositiveSmallIntegerField(default=10)
    order = models.PositiveSmallIntegerField(unique=True, default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} (0–{self.max_score})"


class Result(models.Model):
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='results')
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE, related_name='results')
    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE, related_name='results')

    exam = models.PositiveSmallIntegerField(default=0, help_text='Examination score, 0–70.')
    total = models.PositiveSmallIntegerField(default=0, editable=False)
    grade = models.CharField(max_length=2, blank=True, editable=False)
    remark = models.CharField(max_length=50, blank=True, editable=False)

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='results_entered',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'subject', 'term')
        ordering = ['subject__name']

    def __str__(self):
        return f"{self.student} — {self.subject} — {self.term} — {self.total}"

    def save(self, *args, **kwargs):
        self.exam = min(self.exam, 70)
        super().save(*args, **kwargs)

    def recompute(self):
        """Total/grade depend on ResultComponentScore rows that can only
        exist once this Result already has a pk — so unlike the old single-
        `ca`-field model, these can't be computed inside save() itself.
        Call this explicitly once the component scores are saved (see
        results.services.save_result_scores, the single path that does this)."""
        from django.db.models import Sum
        ca_total = self.component_scores.aggregate(s=Sum('value'))['s'] or 0
        self.total = ca_total + self.exam
        boundary = GradeBoundary.for_score(self.total)
        self.grade = boundary.grade if boundary else ''
        self.remark = boundary.remark if boundary else ''
        self.save(update_fields=['total', 'grade', 'remark'])


class ResultComponentScore(models.Model):
    result = models.ForeignKey(Result, on_delete=models.CASCADE, related_name='component_scores')
    component = models.ForeignKey(ScoreComponent, on_delete=models.CASCADE, related_name='scores')
    value = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ('result', 'component')
        ordering = ['component__order']

    def __str__(self):
        return f"{self.result} — {self.component.name}: {self.value}"

    def save(self, *args, **kwargs):
        self.value = min(self.value, self.component.max_score)
        super().save(*args, **kwargs)
