# Signals in this file:
# 1. post_save on User → create UserProfile
# 2. post_save on User → update related data (if needed)

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile

# Get the User model (best practice - works with custom user models)
User = get_user_model()


# SIGNAL 1: AUTO-CREATE USER PROFILE
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create UserProfile when User is created

    This signal handler:
    1. Listens for post_save signal on User model
    2. Checks if this is a NEW user (created=True)
    3. Creates UserProfile for the new user

    Args:
        sender (Model class): The model class (User)
        instance (User): The actual user instance that was saved
        created (bool): True if this is a new user, False if updating existing
        **kwargs: Additional arguments
    """
    if created:
        if created:
            profile, created_profile = UserProfile.objects.get_or_create(user=instance)
            if created_profile:
                profile.theme = 'light'
                profile.email_notifications = True
                profile.save()

        # Log the action
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
    """
    Cleanup actions before user is deleted

    This signal handler:
    1. Runs BEFORE user is deleted (pre_delete)
    2. Performs cleanup actions
    3. Logs the deletion

    Args:
        sender (Model class): User model
        instance (User): The user being deleted
        **kwargs: Additional arguments

    Cleanup actions:
    - Delete avatar file from storage
    - Unassign leads (reassign to manager)
    - Log deletion for audit trail
    """
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


# ==============================================================================
# TESTING SIGNALS

# Test in Django shell (python manage.py shell):
#
# from django.contrib.auth import get_user_model
# User = get_user_model()
#
# # Test 1: Profile auto-creation
# user = User.objects.create_user(
#     email='test@clinic.com',
#     password='testpass123',
#     first_name='Test',
#     last_name='User'
# )
# print(user.profile)  # Should work (not error)
# print(user.profile.language)  # Should be 'ar'
#
# # Test 2: Profile exists for all users
# for user in User.objects.all():
#     assert hasattr(user, 'profile')
#     print(f"{user.email} → {user.profile}")
#
# # Test 3: Deletion cleanup
# user = User.objects.first()
# print(f"Deleting: {user.email}")
# user.delete()  # Should see cleanup messages
#
# ==============================================================================


# ==============================================================================
# SIGNAL BEST PRACTICES
# ==============================================================================
#
# ✅ DO:
# - Use signals for side effects (create related objects)
# - Use signals for cleanup (delete files, reassign data)
# - Use signals for audit logging
# - Keep signal handlers SHORT and FAST
# - Handle exceptions gracefully
#
# ❌ DON'T:
# - Don't put business logic in signals
# - Don't make external API calls in signals
# - Don't create circular signal loops
# - Don't use signals for complex calculations
# - Don't block the save operation
#
# ALTERNATIVES:
# - For complex logic → use services layer
# - For API calls → use Celery tasks
# - For calculations → use model methods
#
# ==============================================================================


# ==============================================================================
# DEBUGGING SIGNALS
# ==============================================================================
#
# If signals don't work:
#
# 1. Check apps.py imports signals:
#    def ready(self):
#        import apps.accounts.signals
#
# 2. Check app is in INSTALLED_APPS:
#    'apps.accounts',
#
# 3. Check signal is registered:
#    from django.db.models.signals import post_save
#    print(post_save.receivers)  # Should include our handler
#
# 4. Add print statements:
#    print("Signal fired!")
#    print(f"Created: {created}")
#    print(f"Instance: {instance}")
#
# 5. Check for exceptions:
#    Try creating user in shell and watch for errors
#
# ==============================================================================