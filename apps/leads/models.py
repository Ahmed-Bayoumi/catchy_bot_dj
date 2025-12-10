from django.db import models
from django.utils import timezone
from django.urls import reverse
from apps.accounts.models import User
from apps.core.models import Company, LeadSource, LeadStage
from taggit.managers import TaggableManager

class Lead(models.Model):
    
    # Status choices
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('converted', 'Converted'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ]
    
    # Priority choices
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]
    
    # Basic Information
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='leads', help_text='Which company/clinic owns this lead')
    name = models.CharField(max_length=200, help_text="Lead's full name")
    phone = models.CharField(max_length=20, db_index=True, help_text='Phone number in international format')
    email = models.EmailField(blank=True, null=True, help_text='Email address (optional)')
    
    # Lead Classification
    source = models.ForeignKey(LeadSource, on_delete=models.PROTECT, related_name='leads', help_text='Where did this lead come from?')
    stage = models.ForeignKey(LeadStage, on_delete=models.PROTECT, related_name='leads', help_text='Current stage in the lead lifecycle')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', db_index=True, help_text='Current internal status')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', help_text='How urgent is this lead?')

    # Assignment & Management
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_leads', db_index=True, help_text='Which agent is responsible for this lead')
    next_follow_up = models.DateTimeField(null=True, blank=True, db_index=True, help_text='When is the next follow-up scheduled?')
    
    # Additional Information
    notes = models.TextField(blank=True, help_text='General notes about this lead')
    tags = TaggableManager(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, help_text='When was this lead created')
    updated_at = models.DateTimeField(auto_now=True, help_text='When was this lead last updated')
    
    class Meta:
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'
        ordering = ['-created_at']
        unique_together = ['company', 'phone']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['company', 'stage']),
            models.Index(fields=['company', 'assigned_to']),
            models.Index(fields=['created_at']),
            models.Index(fields=['next_follow_up']),
        ]
    
    def __str__(self):
        """String representation: Name (Phone) - Status"""
        return f"{self.name} ({self.phone}) - {self.get_status_display()}"
    
    def get_absolute_url(self):
        """Returns URL to lead detail page"""
        return reverse('leads:lead_detail', kwargs={'pk': self.pk})
    
    def get_full_name(self):
        """Returns the lead's full name"""
        return self.name
    
    def get_initials(self):
        """Returns first letters for avatar: 'Ahmed Ali' → 'AA'"""
        parts = self.name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[1][0]}".upper()
        elif len(parts) == 1:
            return parts[0][0].upper()
        return "?"
    
    def can_be_assigned(self):
        """Check if lead can be assigned (not won/lost)"""
        return self.status not in ['won', 'lost']
    
    def assign_to(self, user, assigned_by=None):
        """
        Assign lead to user (agent)
        Updates assigned_to field, creates activity log, updates user statistics
        """
        if not self.can_be_assigned():
            return False
        
        old_assignee = self.assigned_to
        self.assigned_to = user
        self.save()
        
        # Create activity log
        Activity.objects.create(
            lead=self,
            user=assigned_by or user,
            activity_type='assigned',
            description=f'Assigned to {user.get_full_name()}'
        )
        
        # Update user statistics
        if user:
            user.total_leads_assigned += 1
            user.save(update_fields=['total_leads_assigned'])
        
        if old_assignee and old_assignee != user:
            old_assignee.total_leads_assigned = max(0, old_assignee.total_leads_assigned - 1)
            old_assignee.save(update_fields=['total_leads_assigned'])
        
        return True
    
    def change_stage(self, new_stage, user=None):

        old_stage = self.stage
        self.stage = new_stage
        self.save()
        
        Activity.objects.create(
            lead=self,
            user=user,
            activity_type='stage_changed',
            description=f'Stage changed from "{old_stage.name}" to "{new_stage.name}"'
        )
    
    def change_status(self, new_status, user=None):

        old_status = self.status
        self.status = new_status
        self.save()
        
        # Update user statistics
        if self.assigned_to:
            if new_status == 'converted':
                self.assigned_to.total_leads_converted += 1
                self.assigned_to.save(update_fields=['total_leads_converted'])
            elif new_status == 'won':
                self.assigned_to.total_leads_won += 1
                self.assigned_to.save(update_fields=['total_leads_won'])
        
        # Create activity log
        status_display = dict(self.STATUS_CHOICES).get(new_status, new_status)
        old_status_display = dict(self.STATUS_CHOICES).get(old_status, old_status)
        Activity.objects.create(
            lead=self,
            user=user,
            activity_type='status_changed',
            description=f'Status changed from "{old_status_display}" to "{status_display}"'
        )
    
    def add_note(self, content, user):

        note = Note.objects.create(
            lead=self,
            user=user,
            content=content
        )
        
        # Create activity log
        Activity.objects.create(
            lead=self,
            user=user,
            activity_type='note_added',
            description='Added a note'
        )
        
        return note
    
    def get_activities(self):
        """Get all activities for this lead (ordered newest first)"""
        return self.activities.all().select_related('user').order_by('-created_at')
    
    def get_notes(self):
        """Get all notes for this lead (ordered newest first)"""
        return self.notes_set.all().select_related('user').order_by('-created_at')
    
    def time_since_created(self):
        """Returns time elapsed since lead was created"""
        delta = timezone.now() - self.created_at
        
        if delta.days > 30:
            months = delta.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    def time_until_follow_up(self):
        """Returns time until next follow-up"""
        if not self.next_follow_up:
            return None
        
        delta = self.next_follow_up - timezone.now()
        
        if delta.total_seconds() < 0:
            return "Overdue"
        
        if delta.days > 0:
            return f"In {delta.days} day{'s' if delta.days > 1 else ''}"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"In {hours} hour{'s' if hours > 1 else ''}"
        else:
            minutes = delta.seconds // 60
            return f"In {minutes} minute{'s' if minutes > 1 else ''}"


class Note(models.Model):

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='notes_set', help_text='Which lead this note belongs to')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='notes', help_text='Who wrote this note')
    content = models.TextField(help_text='Note text/content')
    created_at = models.DateTimeField(auto_now_add=True, help_text='When was this note created')
    
    class Meta:
        verbose_name = 'Note'
        verbose_name_plural = 'Notes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['lead', '-created_at']),
        ]
    
    def __str__(self):
        """String representation"""
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"Note by {self.user.get_full_name() if self.user else 'Unknown'}: {preview}"


class Activity(models.Model):
    
    # Activity type choices
    ACTIVITY_TYPE_CHOICES = [
        ('created', 'Created'),
        ('assigned', 'Assigned'),
        ('status_changed', 'Status Changed'),
        ('stage_changed', 'Stage Changed'),
        ('note_added', 'Note Added'),
        ('contacted', 'Contacted'),
        ('email_sent', 'Email Sent'),
        ('call_logged', 'Call Logged'),
    ]
    
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities', help_text='Which lead this activity is for')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activities', help_text='Who performed this action')
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPE_CHOICES, help_text='Type of activity/action')
    description = models.TextField(help_text='Human-readable description of what happened')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, help_text='When did this activity occur')
    
    class Meta:
        verbose_name = 'Activity'
        verbose_name_plural = 'Activities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['lead', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        """String representation"""
        user_name = self.user.get_full_name() if self.user else 'System'
        return f"{user_name}: {self.description}"