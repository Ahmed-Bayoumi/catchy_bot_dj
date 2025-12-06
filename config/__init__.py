# ==============================================================================
# CATCHY BOT CRM - CONFIG PACKAGE INITIALIZER
# ==============================================================================

# Import Celery app to ensure it's loaded when Django starts
# This ensures that:
# 1. Celery is configured with Django settings
# 2. All tasks are discovered automatically
# 3. Celery beat scheduler is initialized
from .celery import app as celery_app

# Make celery_app available at package level
# This allows importing as: from config import celery_app
__all__ = ('celery_app',)