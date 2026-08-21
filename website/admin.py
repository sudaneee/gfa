from django.contrib import admin
from django.shortcuts import redirect

from website.models import ContactMessage, SchoolSettings


@admin.register(SchoolSettings)
class SchoolSettingsAdmin(admin.ModelAdmin):
    """
    Singleton admin: skip the changelist entirely and go straight to the
    (only) change form, since there is exactly one SchoolSettings row.
    """

    def has_add_permission(self, request):
        return not SchoolSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = SchoolSettings.get_solo()
        return redirect('admin:website_schoolsettings_change', obj.pk)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'phone', 'email', 'is_read', 'created_at')
    list_filter = ('subject', 'is_read')
    search_fields = ('name', 'email', 'phone', 'message')
