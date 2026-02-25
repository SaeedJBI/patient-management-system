from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    path('download/<uuid:file_id>/', views.serve_private_file, name='file_download'),
    path('upload/', views.file_upload, name='file_upload'),
]