# Celery is a distributed task queue for running background jobs

# - Send emails asynchronously
# - Process WhatsApp webhooks
# - Generate reports
# - Send scheduled notifications
# - Clean up old data
#
# Start worker: celery -A config worker -l info
# Start beat: celery -A config beat -l info
# ==============================================================================

import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for Celery
# This ensures Celery uses the same settings as Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create Celery app instance
# 'catchybot' is the app name (appears in logs and monitoring)
app = Celery('catchybot')

# Load Celery configuration from Django settings
# All settings prefixed with 'CELERY_' will be used
# Example: CELERY_BROKER_URL, CELERY_RESULT_BACKEND
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
# Looks for tasks.py file in each app
# Example: apps/whatsapp/tasks.py, apps/leads/tasks.py
app.autodiscover_tasks()


# CELERY BEAT SCHEDULE (Periodic Tasks)

# Schedule periodic tasks to run at specific intervals
# Beat scheduler reads this and triggers tasks automatically
app.conf.beat_schedule = {
    # Example: Send daily report at 9 AM
    'send-daily-report': {
        'task': 'apps.reports.tasks.send_daily_report',
        'schedule': crontab(hour=9, minute=0),  # Every day at 9:00 AM
    },

    # Example: Clean up old messages every Sunday at 2 AM
    'cleanup-old-messages': {
        'task': 'apps.chat.tasks.cleanup_old_messages',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Sunday 2:00 AM
    },

    # Example: Update lead statistics every hour
    'update-lead-statistics': {
        'task': 'apps.leads.tasks.update_statistics',
        'schedule': crontab(minute=0),  # Every hour at minute 0
    },

    # Example: Send pending appointment reminders every 15 minutes
    'send-appointment-reminders': {
        'task': 'apps.appointments.tasks.send_reminders',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
}


# CELERY TASK ANNOTATIONS

# Configure specific tasks
app.conf.task_annotations = {
    # Set time limits for specific tasks
    'apps.reports.tasks.generate_monthly_report': {
        'time_limit': 600,  # 10 minutes
        'soft_time_limit': 540,  # 9 minutes
    },

    # Set rate limits (prevent overwhelming external APIs)
    'apps.whatsapp.tasks.send_whatsapp_message': {
        'rate_limit': '10/m',  # Maximum 10 messages per minute
    },
}


# CELERY DEBUG TASK (for testing)

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Debug task to test Celery is working

    Usage:
        from config.celery import debug_task
        debug_task.delay()
    """
    print(f'Request: {self.request!r}')


# CELERY SIGNALS (Optional)

# You can add signal handlers here for monitoring
# Example:

# from celery.signals import task_success, task_failure

# @task_success.connect
# def task_success_handler(sender=None, result=None, **kwargs):
#     """
#     Called when task succeeds
#     Can be used for logging, notifications, etc.
#     """
#     print(f'Task {sender.name} succeeded with result: {result}')

# @task_failure.connect
# def task_failure_handler(sender=None, exception=None, **kwargs):
#     """
#     Called when task fails
#     Can be used for error tracking (Sentry, etc.)
#     """
#     print(f'Task {sender.name} failed with exception: {exception}')



# CRONTAB EXAMPLES (for reference)
# ==============================================================================
#
# crontab(minute=0, hour=0)              # Every day at midnight
# crontab(minute=0, hour='*/3')          # Every 3 hours
# crontab(minute=0, hour=0, day_of_week=1) # Every Monday at midnight
# crontab(minute=0, hour=0, day_of_month=1) # First day of month at midnight
# crontab(minute='*/15')                  # Every 15 minutes
# crontab(minute=0, hour='8-17')         # Every hour between 8 AM and 5 PM
#
# ==============================================================================