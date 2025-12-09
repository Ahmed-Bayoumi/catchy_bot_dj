from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Lead, Activity


@receiver(post_save, sender=Lead)
def create_lead_activity(sender, instance, created, **kwargs):

    # Only run for newly created leads (not updates)
    if created:
        # Create activity log entry
        Activity.objects.create(
            lead=instance,
            user=None,  # System-generated (no specific user)
            activity_type='created',
            description=f'Lead created'
        )


@receiver(pre_save, sender=Lead)
def track_lead_changes(sender, instance, **kwargs):
    # Check if this is an update (not a new lead)
    if instance.pk:
        try:
            old_lead = Lead.objects.get(pk=instance.pk)

            # Store old values as temporary attributes
            instance._old_status = old_lead.status
            instance._old_stage = old_lead.stage
            instance._old_assigned_to = old_lead.assigned_to

        except Lead.DoesNotExist:
            # Lead was deleted between check and save (rare race condition)
            pass


# Alternative approach: Logging status/stage changes automatically in signal
# This is commented out because we prefer explicit logging in model methods
# Uncomment if you want fully automatic activity logging

"""
@receiver(post_save, sender=Lead)
def log_lead_status_change(sender, instance, created, **kwargs):
    '''
    Automatically log status/stage changes

    Note: This approach logs changes automatically but doesn't know
    which user made the change. The model method approach is better
    because it includes user information.
    '''

    if not created and hasattr(instance, '_old_status'):
        # Status changed
        if instance._old_status != instance.status:
            Activity.objects.create(
                lead=instance,
                user=None,
                activity_type='status_changed',
                description=f'Status changed from "{instance._old_status}" to "{instance.status}"'
            )

        # Stage changed
        if hasattr(instance, '_old_stage') and instance._old_stage != instance.stage:
            old_stage_name = instance._old_stage.name if instance._old_stage else 'Not specified'
            Activity.objects.create(
                lead=instance,
                user=None,
                activity_type='stage_changed',
                description=f'Stage changed from "{old_stage_name}" to "{instance.stage.name}"'
            )

        # Assignment changed
        if hasattr(instance, '_old_assigned_to') and instance._old_assigned_to != instance.assigned_to:
            if instance.assigned_to:
                Activity.objects.create(
                    lead=instance,
                    user=None,
                    activity_type='assigned',
                    description=f'Lead assigned to {instance.assigned_to.get_full_name()}'
                )
            else:
                Activity.objects.create(
                    lead=instance,
                    user=None,
                    activity_type='assigned',
                    description='Lead assignment removed'
                )
"""

from .models import Note

@receiver(post_save, sender=Note)
def log_note_creation(sender, instance, created, **kwargs):
    if created:
        # Check if activity was already created (avoid duplicates)
        # This checks if an activity was created in the last 1 second
        from django.utils import timezone
        from datetime import timedelta

        recent_activity = Activity.objects.filter(
            lead=instance.lead,
            activity_type='note_added',
            created_at__gte=timezone.now() - timedelta(seconds=1)
        ).exists()

        # Only create activity if one doesn't already exist
        if not recent_activity:
            Activity.objects.create(
                lead=instance.lead,
                user=instance.user,
                activity_type='note_added',
                description=f'Added a note'
            )