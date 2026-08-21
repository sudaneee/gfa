from django.urls import path

from results import views

app_name = 'results'

urlpatterns = [
    path('entry/', views.enter_results, name='entry'),
    path('entry/template/', views.download_result_template, name='download_template'),
    path('entry/upload/', views.upload_results, name='upload'),
    path('update/', views.update_results, name='update'),
    path('broadsheet/', views.broadsheet, name='broadsheet'),
    path('broadsheet/pdf/', views.class_results_pdf, name='class_results_pdf'),
    path('report-cards/', views.report_cards, name='report_cards'),
    path('report-card/<int:student_id>/<int:term_id>/', views.report_card, name='report_card'),
    path('report-card/<int:student_id>/<int:term_id>/pdf/', views.report_card_pdf, name='report_card_pdf'),
]
