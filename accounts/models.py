from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model so every account in the system — administrator,
    teacher, parent, student — carries a `role` that drives which portal
    and which data they can see (see accounts.decorators.role_required).

    Pattern ported from makarfi/src/models/user_models.py, roles narrowed
    to the four that matter for a K-12 school rather than a tertiary ERP's
    long staff-title list.
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', 'Administrator'
        TEACHER = 'teacher', 'Teacher'
        PARENT = 'parent', 'Parent'
        STUDENT = 'student', 'Student'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADMIN)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"
