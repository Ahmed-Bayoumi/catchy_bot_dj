from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountsConfig(AppConfig):
    """
    Configuration class for accounts app

    This class:
    1. Sets the app name and label
    2. Registers signals when Django starts
    3. Configures default field type for auto-generated IDs

    Signals registered:
    - post_save on User → creates UserProfile automatically
    - This ensures every user has a profile (no need to create manually)
    """

    # Default field type for auto-generated primary keys
    # BigAutoField = 64-bit integer (can store up to 9,223,372,036,854,775,807)
    # Better than AutoField (32-bit) for future-proofing
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'

    # Human-readable app name (shown in admin panel)
    verbose_name = _('Accounts')

    def ready(self):
        """
        Called when Django starts

        This method:
        1. Runs once when app is loaded
        2. Perfect place to register signals
        3. Import models and connect signal handlers

        Signals imported here:
        - apps/accounts/signals.py

        Why import here?
        - Ensures signals are registered before any code runs
        - Prevents "AppRegistryNotReady" errors
        - Follows Django best practices
        """
        # Import signals module to register signal handlers
        import apps.accounts.signals
