from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile


User = get_user_model()


# SIGNAL 1: AUTO-CREATE USER PROFILE
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if created:
            profile, created_profile = UserProfile.objects.get_or_create(user=instance)
            if created_profile:
                profile.theme = 'light'
                profile.email_notifications = True
                profile.save()

        print(f"✅ Profile created for user: {instance.email}")

#
# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     """
#     Save UserProfile when User is saved
#
#     This ensures profile is saved whenever user is saved
#     Useful if you update profile fields along with user fields
#
#     Args:
#         sender (Model class): User model
#         instance (User): The user instance being saved
#         **kwargs: Additional arguments
#
#     Note:
#     - This runs for BOTH new and existing users
#     - For new users: profile was just created by create_user_profile()
#     - For existing users: ensures profile stays in sync
#     """
#     # Check if profile exists (should always exist after create_user_profile)
#     if hasattr(instance, 'profile'):
#         instance.profile.save()




# SIGNAL 2: CLEANUP ON USER DELETION
@receiver(pre_delete, sender=User)
def delete_user_cleanup(sender, instance, **kwargs):
    # Delete avatar file from storage (if exists)
    if instance.avatar:
        try:
            instance.avatar.delete(save=False)
            print(f"🗑️ Deleted avatar for user: {instance.email}")
        except Exception as e:
            print(f"⚠️ Error deleting avatar: {e}")

    # Log deletion (for audit trail)
    print(f"🗑️ User deleted: {instance.email} ({instance.get_full_name()})")

    # Optional: Reassign user's leads to manager before deletion
    # from apps.leads.models import Lead
    # if instance.company and instance.company.owner:
    #     # Find all leads assigned to this user
    #     leads = Lead.objects.filter(assigned_to=instance)
    #     # Reassign to company owner (admin)
    #     leads.update(assigned_to=instance.company.owner)
    #     print(f"📋 Reassigned {leads.count()} leads to company owner")




# SIGNAL 3: UPDATE USER STATISTICS (OPTIONAL)

# Uncomment this when Lead model is created (Phase 3)
#
# @receiver(post_save, sender='leads.Lead')
# def update_user_lead_stats(sender, instance, created, **kwargs):
#     """
#     Update user statistics when lead status changes
#
#     This automatically updates:
#     - total_leads_assigned
#     - total_leads_converted
#     - total_leads_won
#
#     Triggered by:
#     - Lead created
#     - Lead status changed
#     """
#     if not instance.assigned_to:
#         return
#
#     user = instance.assigned_to
#
#     # Recalculate statistics
#     from apps.leads.models import Lead
#
#     # Total assigned to this user
#     user.total_leads_assigned = Lead.objects.filter(
#         assigned_to=user
#     ).count()
#
#     # Total converted (stage = patient)
#     user.total_leads_converted = Lead.objects.filter(
#         assigned_to=user,
#         stage='patient'
#     ).count()
#
#     # Total won (status = won)
#     user.total_leads_won = Lead.objects.filter(
#         assigned_to=user,
#         status='won'
#     ).count()
#
#     # Save updated statistics
#     user.save(update_fields=[
#         'total_leads_assigned',
#         'total_leads_converted',
#         'total_leads_won'
#     ])
