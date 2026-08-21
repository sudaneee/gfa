from django.contrib import admin

from communication.models import Announcement, Event


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'audience', 'is_published', 'created_at')
    list_filter = ('audience', 'is_published')
    search_fields = ('title', 'content')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'date')
    list_filter = ('category',)
    search_fields = ('title', 'description')
