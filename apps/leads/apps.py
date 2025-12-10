from django.apps import AppConfig


class LeadsConfig(AppConfig):

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.leads'
    verbose_name = 'Lead Management'

    def ready(self):
        try:
            import apps.leads.signals
        except ImportError:
            pass