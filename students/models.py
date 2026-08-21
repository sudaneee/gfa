from django.conf import settings
from django.db import models
from django.utils import timezone


class Guardian(models.Model):
    RELATIONSHIP_CHOICES = [('Father', 'Father'), ('Mother', 'Mother'), ('Guardian', 'Guardian')]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='guardian_profile',
    )
    name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES, default='Father')
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    occupation = models.CharField(max_length=150, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


def generate_admission_number(school_class):
    """GFA/<LEVELCODE>/<year>/<seq> — matches the frontend prototype's format."""
    level_code = (school_class.level[:3] if school_class else 'GEN').upper()
    year = timezone.localdate().year
    prefix = f"GFA/{level_code}/{year}/"
    last = Student.objects.filter(admission_number__startswith=prefix).order_by('-admission_number').first()
    next_seq = int(last.admission_number.rsplit('/', 1)[-1]) + 1 if last else 1
    return f"{prefix}{next_seq:03d}"


def student_photo_path(instance, filename):
    return f"students/{instance.admission_number or 'pending'}/{filename}"


class Student(models.Model):
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female')]
    STATUS_CHOICES = [('Active', 'Active'), ('Inactive', 'Inactive')]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='student_profile',
    )
    admission_number = models.CharField(max_length=30, unique=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to=student_photo_path, blank=True, null=True)

    school_class = models.ForeignKey('academics.SchoolClass', on_delete=models.PROTECT, related_name='students')
    section = models.ForeignKey('academics.Section', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    guardian = models.ForeignKey(Guardian, on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    admission_date = models.DateField(default=timezone.localdate)

    # Set when an admitted Application is converted into an enrolled Student
    # (Phase 2's other end) — nullable since students can also be added
    # directly by admin without ever having applied online.
    application = models.OneToOneField(
        'admissions.Application', on_delete=models.SET_NULL, null=True, blank=True, related_name='student',
    )

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.full_name} ({self.admission_number})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def class_label(self):
        return f"{self.school_class}{self.section.name if self.section else ''}"

    def save(self, *args, **kwargs):
        if not self.admission_number:
            self.admission_number = generate_admission_number(self.school_class)
        super().save(*args, **kwargs)
