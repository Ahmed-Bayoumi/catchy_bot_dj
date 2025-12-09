from celery import shared_task
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_reminders():
    """
    Periodic task to send appointment reminders.
    Scheduled in config/celery.py
    """
    logger.info("Checking for appointments needing reminders...")
    # Placeholder for actual reminder logic
    return "Checked appointments"
