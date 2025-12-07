from django.urls import path
from . import views

# Namespace for core app URLs
# Usage in templates: {% url 'core:dashboard' %}
app_name = 'core'

urlpatterns = [
    # Dashboard - Main page after login
    path('', views.dashboard_view, name='dashboard'),
    path('settings/company/', views.company_settings_view, name='company_settings'),
]

