from django.urls import path

from admissions import views

app_name = 'admissions'

urlpatterns = [
    path('', views.info, name='info'),
    path('apply/', views.apply_start, name='apply'),
    path('apply/payment/', views.apply_payment, name='apply_payment'),
    path('apply/continue/<str:application_number>/<str:resume_token>/', views.apply_continue, name='apply_continue'),
    path('apply/applicant/', views.apply_applicant, name='apply_applicant'),
    path('apply/guardian/', views.apply_guardian, name='apply_guardian'),
    path('apply/academic/', views.apply_academic, name='apply_academic'),
    path('apply/documents/', views.apply_documents, name='apply_documents'),
    path('apply/review/', views.apply_review, name='apply_review'),
    path('apply/success/<str:application_number>/', views.apply_success, name='apply_success'),
    path('track/', views.track, name='track'),
]
