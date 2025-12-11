from celery import shared_task
from django.utils import timezone
from .models import Lead
from apps.accounts.models import User

@shared_task
def send_follow_up_notifications():
    now = timezone.now()
    leads = Lead.objects.filter(
        next_follow_up__lte=now,
        status__in=['new','contacted','qualified']
    )

    notifications_sent = 0

    for lead in leads:
        if lead.assigned_to:
            lead.activities.create(
                user=None,
                activity_type='follow_up_reminder',
                description=f'Follow-up reminder for lead "{lead.name}"'
            )
            notifications_sent += 1

    return f'{notifications_sent} follow-up notifications sent.'
