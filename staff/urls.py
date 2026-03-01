from django.urls import path
from . import views

app_name = 'staff'

urlpatterns = [
    # Keep only ONE entry per view with consistent naming
    path('', views.dashboard, name='dashboard'),
    path('search/', views.patient_search, name='patient_search'),
    path('recent/', views.recent_patients, name='recent_patients'),
    path('uploads/', views.file_uploads, name='file_uploads'),
    path('profile/', views.staff_profile, name='profile'),
    path('patient/<uuid:patient_id>/', views.patient_detail, name='patient_detail'),
    path('add-patient/', views.receptionist_add_patient, name='receptionist_add_patient'),
]