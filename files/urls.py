from django.urls import path
from . import views

app_name = 'files'

urlpatterns = [
    path('download/<uuid:file_id>/', views.serve_file, name='file_download'),
    path('preview/<uuid:file_id>/', views.serve_file, name='file_preview'),
    path('upload/', views.file_upload, name='file_upload'),
]