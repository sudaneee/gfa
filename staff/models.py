from django.conf import settings
from django.db import models
from django.utils import timezone


def generate_staff_id():
    year_suffix = timezone.localdate().year
    last = Teacher.objects.order_by('-id').first()
    next_seq = (last.id + 1) if last else 1
    return f"GFA/STAFF/{next_seq:03d}"


class Teacher(models.Model):
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female')]
    STATUS_CHOICES = [('Active', 'Active'), ('Inactive', 'Inactive')]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='teacher_profile',
    )
    staff_id = models.CharField(max_length=30, unique=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    department = models.CharField(max_length=100, blank=True)
    qualification = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    employment_date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')

    subjects = models.ManyToManyField('academics.Subject', blank=True, related_name='teachers')
    sections = models.ManyToManyField('academics.Section', blank=True, related_name='teachers')

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.full_name} ({self.staff_id})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.staff_id:
            self.staff_id = generate_staff_id()
        super().save(*args, **kwargs)
