from django.urls import path
from . import views


app_name = 'core'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('select-company/', views.company_selector_view, name='company_selector'),
    path('settings/company/', views.company_settings_view, name='company_settings'),
    path('settings/company/deactivate/', views.deactivate_company_view, name='company_deactivate'),
]

