from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    path('', views.search_page, name='page'),
    path('api/', views.search_api, name='api'),
    path('show-all/', views.show_all_api, name='show_all'),
    path('suggest/', views.search_suggestions, name='suggest'),
]