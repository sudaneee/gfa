from django.contrib import admin

from attendance.models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'section', 'date', 'status', 'marked_by')
    list_filter = ('status', 'section', 'date')
    search_fields = ('student__first_name', 'student__last_name', 'student__admission_number')
    date_hierarchy = 'date'
