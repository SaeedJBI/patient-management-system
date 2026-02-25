from django.urls import path
from . import views

app_name = 'branches'

urlpatterns = [
    path('api/', views.branch_list_api, name='api'),
]