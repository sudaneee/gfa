"""
config URL Configuration

Only accounts/website/portal are wired so far (Phase 0 scaffold). Each
subsequent app (admissions, payments, academics, students, staff,
attendance, results, examinations, finance, communication) gets its own
include() here as that phase is built out.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('website.urls')),
    path('', include('accounts.urls')),
    path('admissions/', include('admissions.urls')),
    path('payments/', include('payments.urls')),
    path('attendance/', include('attendance.urls')),
    path('results/', include('results.urls')),
    path('portal/', include('portal.urls')),
    path('console/', include('admin_console.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
