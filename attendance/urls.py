from django.urls import path

from attendance import views

app_name = 'attendance'

urlpatterns = [
    path('mark/', views.mark_attendance, name='mark'),
    path('records/', views.attendance_records, name='records'),
]
