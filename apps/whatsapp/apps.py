from django.apps import AppConfig

class WhatsappConfig(AppConfig):

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.whatsapp'
    verbose_name = 'WhatsApp integration'

    # def ready(self):
    #     try:
    #         import apps.whatsapp.signals
    #     except ImportError:
    #         pass