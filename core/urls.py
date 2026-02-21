from django.urls import path
from . import views

app_name = 'core'  # This is important

urlpatterns = [
    path('set-language/', views.set_language, name='set-language'),
]