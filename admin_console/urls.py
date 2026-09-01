from django.urls import path

from admin_console import views

app_name = 'admin_console'

urlpatterns = [
    path('', views.console_home, name='home'),

    path('applications/', views.applications_list, name='applications_list'),
    path('applications/<int:pk>/', views.application_detail, name='application_detail'),
    path('applications/<int:pk>/enroll/', views.application_enroll, name='application_enroll'),

    path('invoices/', views.invoices_list, name='invoices_list'),

    path('payments/', views.payments_list, name='payments_list'),
    path('payments/mark-received/', views.payment_mark_received, name='payment_mark_received'),

    path('fee-structures/', views.fee_structures_list, name='fee_structures_list'),
    path('fee-structures/add/', views.fee_structure_create, name='fee_structure_create'),
    path('fee-structures/<int:pk>/edit/', views.fee_structure_edit, name='fee_structure_edit'),
    path('fee-structures/<int:pk>/delete/', views.fee_structure_delete, name='fee_structure_delete'),

    path('<slug:slug>/', views.generic_list, name='list'),
    path('<slug:slug>/add/', views.generic_create, name='create'),
    path('<slug:slug>/<int:pk>/edit/', views.generic_edit, name='edit'),
    path('<slug:slug>/<int:pk>/delete/', views.generic_delete, name='delete'),
]
