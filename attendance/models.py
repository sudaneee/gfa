from django.conf import settings
from django.db import models


class AttendanceRecord(models.Model):
    STATUS_CHOICES = [('Present', 'Present'), ('Absent', 'Absent'), ('Late', 'Late')]

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='attendance_records')
    section = models.ForeignKey('academics.Section', on_delete=models.CASCADE, related_name='attendance_records')
    term = models.ForeignKey('academics.Term', on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Present')
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_marked',
    )
    marked_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.student} — {self.date} — {self.status}"
