from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    path('download/<uuid:file_id>/', views.serve_private_file, name='download'),
]