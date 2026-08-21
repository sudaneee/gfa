from django.urls import path

from portal import views

app_name = 'portal'

urlpatterns = [
    path('', views.home, name='home'),
    path('reports/', views.reports, name='reports'),
    path('settings/', views.settings_view, name='settings'),
    path('settings/edit/', views.settings_edit, name='settings_edit'),
    path('settings/reset-demo-data/', views.reset_demo_data_view, name='reset_demo_data'),
]
