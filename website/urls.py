from django.urls import path

from website import views

app_name = 'website'

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('academics/', views.academics, name='academics'),
    path('facilities/', views.facilities, name='facilities'),
    path('contact/', views.contact, name='contact'),
    path('news-events/', views.news_events, name='news_events'),
]
