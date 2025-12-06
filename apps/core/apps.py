from django.apps import AppConfig


class CoreConfig(AppConfig):
    """
    Configuration for Core application

    This app contains:
        - Company model (multi-tenancy)
        - LeadSource model (where leads come from)
        - LeadStage model (lead lifecycle stages)
        - Dashboard view
        - Company settings

    The core app is fundamental to the CRM system as it provides:
        - Multi-tenant isolation
        - Lead classification
        - Central dashboard
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = 'Core'