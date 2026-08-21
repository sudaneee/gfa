from django.contrib import admin

from staff.models import Teacher


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('staff_id', 'full_name', 'gender', 'department', 'status', 'employment_date')
    list_filter = ('department', 'status', 'gender')
    search_fields = ('staff_id', 'first_name', 'last_name', 'email')
    filter_horizontal = ('subjects', 'sections')
