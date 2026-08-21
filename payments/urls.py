from django.urls import path

from payments import views

app_name = 'payments'

urlpatterns = [
    # Admission application fees
    path('application/<str:application_number>/invoice/', views.application_invoice, name='application_invoice'),
    path('application/<str:application_number>/pay/', views.initiate_application_payment, name='initiate_application_payment'),
    path(
        'application/<str:application_number>/payment/<int:payment_pk>/check/',
        views.check_application_payment_status, name='check_application_payment_status',
    ),

    # Termly school fees
    path('fees/<int:student_id>/<int:term_id>/', views.fee_invoice, name='fee_invoice'),
    path('fees/<int:student_id>/<int:term_id>/pay/', views.initiate_fee_payment, name='initiate_fee_payment'),
    path(
        'fees/<int:student_id>/<int:term_id>/payment/<int:payment_pk>/check/',
        views.check_fee_payment_status, name='check_fee_payment_status',
    ),

    # Shared ZainPay callback/webhook
    path('zainpay/callback/', views.zainpay_callback, name='zainpay_callback'),
]
