from django.db import models
from django.utils import timezone


class Announcement(models.Model):
    AUDIENCE_CHOICES = [
        ('all_parents', 'All Parents'),
        ('students', 'Students'),
        ('teachers', 'Teachers'),
        ('staff', 'Staff'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    audience = models.CharField(max_length=20, choices=AUDIENCE_CHOICES, default='all_parents')
    is_published = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='announcements',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Event(models.Model):
    CATEGORY_CHOICES = [
        ('sports', 'Sports'),
        ('debate', 'Debate'),
        ('cultural', 'Cultural'),
        ('meeting', 'Meeting'),
        ('academic', 'Academic'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='academic')
    date = models.DateField()

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.title} — {self.date}"

    @property
    def is_past(self):
        return self.date < timezone.localdate()
