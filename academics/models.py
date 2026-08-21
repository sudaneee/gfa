from django.db import models


class AcademicSession(models.Model):
    """e.g. '2025/2026'. Exactly one is_current=True at a time."""

    name = models.CharField(max_length=20, unique=True)
    is_current = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_current:
            AcademicSession.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_current(cls):
        return cls.objects.filter(is_current=True).first()


class Term(models.Model):
    TERM_CHOICES = [('first', 'First Term'), ('second', 'Second Term'), ('third', 'Third Term')]

    session = models.ForeignKey(AcademicSession, on_delete=models.CASCADE, related_name='terms')
    name = models.CharField(max_length=10, choices=TERM_CHOICES)
    is_current = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('session', 'name')
        ordering = ['session', 'name']

    def __str__(self):
        return f"{self.get_name_display()} — {self.session.name}"

    def save(self, *args, **kwargs):
        if self.is_current:
            Term.objects.exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_current(cls):
        return cls.objects.filter(is_current=True).select_related('session').first()


class FeeBand(models.Model):
    """
    Nursery / Primary / Junior Secondary / Senior Secondary — the 4 bands the
    real fee schedule (PDF) is priced by. Coarser than academic Level: e.g.
    Creche + Pre-Nursery + Nursery classes can all map to the Nursery band.
    Admin-assignable per SchoolClass rather than hardcoded, per the plan.
    """

    name = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name


class SchoolClass(models.Model):
    LEVEL_CHOICES = [
        ('Creche', 'Creche'), ('Pre-Nursery', 'Pre-Nursery'), ('Nursery', 'Nursery'),
        ('Primary', 'Primary'), ('Secondary', 'Secondary'),
    ]

    name = models.CharField(max_length=30, unique=True)  # "Primary 3", "JSS 2"
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    fee_band = models.ForeignKey(FeeBand, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes')
    order = models.PositiveSmallIntegerField(default=0, help_text='Sort order, Creche → SSS3.')

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'School classes'

    def __str__(self):
        return self.name


class Section(models.Model):
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=5)  # "A", "B"

    class Meta:
        unique_together = ('school_class', 'name')
        ordering = ['school_class__order', 'name']

    def __str__(self):
        return f"{self.school_class.name}{self.name}"


class Subject(models.Model):
    LEVEL_CHOICES = SchoolClass.LEVEL_CHOICES

    name = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)

    class Meta:
        unique_together = ('name', 'level')
        ordering = ['level', 'name']

    def __str__(self):
        return f"{self.name} ({self.level})"
