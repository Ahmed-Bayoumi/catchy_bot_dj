from django.db import models
from django.utils.text import slugify
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _


class Company(models.Model):
    """
    Company model - Multi-tenancy core

    Each clinic is a separate company with isolated data.
    Users, leads, messages all belong to a company.

    Features:
        - Basic information (name, logo, description)
        - Contact details (phone, email, website, address)
        - Settings (working hours, timezone)
        - Status tracking (active/inactive)
        - Auto-generated URL slug

    Relationships:
        - One-to-Many with User (company.users)
        - One-to-Many with Lead (company.leads)

    Methods:
        - get_active_users_count() → int: Count of active users
        - get_total_leads_count() → int: Count of all leads
        - get_active_agents_count() → int: Count of active agents

    Example:
        company = Company.objects.create(
            name='Dr. Ahmed Dental Clinic',
            phone='+201234567890',
            email='info@ahmed-clinic.com'
        )
        # Slug auto-generated: 'dr-ahmed-dental-clinic'
    """

    # Basic Information
    name = models.CharField(max_length=200,unique=True,help_text="Company/Clinic name")
    slug = models.SlugField(max_length=200,unique=True,help_text="URL-friendly name (auto-generated)")
    logo = models.ImageField(upload_to='companies/logos/',null=True,blank=True,help_text="Company logo")
    description = models.TextField(blank=True,help_text="Brief description about the company")

    # Contact Information
    phone = models.CharField(max_length=17,blank=True,help_text="Contact phone number")
    email = models.EmailField(blank=True,help_text="Contact email")
    website = models.URLField(blank=True,validators=[URLValidator()],help_text="Company website")
    address = models.TextField(blank=True,help_text="Physical address")

    # Settings
    working_hours = models.CharField(max_length=200,blank=True,help_text="e.g. 9 AM - 5 PM, Sat-Thu")
    timezone = models.CharField(max_length=50,default='Africa/Cairo',help_text="Company timezone")

    # Status
    is_active = models.BooleanField(default=True,help_text="Is company active?")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Override save to auto-generate slug from name

        Process:
            1. Check if slug is empty
            2. Generate slug from name using slugify
            3. Save the model
        """
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_active_users_count(self):
        """
        Get count of active users in this company

        Returns:
            int: Number of active users

        Example:
            company.get_active_users_count()  # 5
        """
        return self.users.filter(is_active=True).count()

    def get_total_leads_count(self):
        """
        Get total leads count

        Note: Will implement after creating Lead model in Phase 3

        Returns:
            int: Number of leads (currently returns 0)
        """
        # TODO: Implement after Lead model is created
        # return self.leads.count()
        return 0

    def get_active_agents_count(self):
        """
        Get count of active agents in this company

        Filters users by:
            - is_active = True
            - role = 'agent'

        Returns:
            int: Number of active agents

        Example:
            company.get_active_agents_count()  # 3
        """
        return self.users.filter(is_active=True, role='agent').count()


class LeadSource(models.Model):
    """
    Source of leads (where they come from)

    Defines different channels through which leads arrive.
    Each source has visual identity (icon, color) for UI display.

    Common Sources:
        - WhatsApp (fab fa-whatsapp, #25D366)
        - Facebook (fab fa-facebook, #1877F2)
        - Instagram (fab fa-instagram, #E4405F)
        - Website (fas fa-globe, #667eea)
        - Referral (fas fa-user-friends, #28a745)
        - Walk-in (fas fa-walking, #6c757d)

    Fields:
        - name: Source name
        - icon: FontAwesome icon class
        - color: Hex color code
        - order: Display order in lists
        - is_active: Active status

    Usage in UI:
        - Dropdown in lead creation form
        - Filters in lead list
        - Charts in dashboard
        - Badges in lead cards

    Example:
        source = LeadSource.objects.create(
            name='WhatsApp',
            icon='fab fa-whatsapp',
            color='#25D366',
            order=1
        )
    """

    name = models.CharField(max_length=100,unique=True,help_text="Source name (e.g. WhatsApp, Facebook)")
    icon = models.CharField(max_length=50,help_text="FontAwesome icon class (e.g. fab fa-whatsapp)")
    color = models.CharField(max_length=7,default='#667eea',help_text="Hex color code (e.g. #25D366 for WhatsApp green)")
    description = models.TextField(blank=True,help_text="Optional description")
    is_active = models.BooleanField(default=True,help_text="Is this source active?")
    order = models.PositiveIntegerField(default=0,help_text="Display order (lower numbers appear first)")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lead Source"
        verbose_name_plural = "Lead Sources"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class LeadStage(models.Model):
    """
    Stages in lead lifecycle (Journey from lead to patient)

    Represents different stages a lead goes through in the sales funnel.
    Used in Kanban board with drag-and-drop functionality.

    Default Stages (in order):
        1. Lead - New inquiry (type: lead)
        2. Contacted - First contact made (type: lead)
        3. Qualified - Potential patient (type: lead)
        4. Patient - Converted to patient (type: patient)
        5. Won - Successfully booked/treated (type: closed)
        6. Lost - Did not convert (type: closed)

    Stage Types:
        - lead: Active leads in pipeline
        - patient: Converted to patient
        - closed: Final stage (won/lost)

    Fields:
        - name: Stage name
        - slug: URL-friendly name
        - stage_type: Type for filtering (lead/patient/closed)
        - color: Hex color for UI
        - icon: FontAwesome icon
        - order: Display order in Kanban

    Usage:
        - Kanban board columns
        - Lead filtering
        - Progress tracking
        - Conversion funnel analysis

    Example:
        stage = LeadStage.objects.create(
            name='Contacted',
            stage_type='lead',
            color='#ffc107',
            icon='fas fa-phone',
            order=2
        )
    """

    STAGE_TYPES = [
        ('lead', 'Lead'),
        ('patient', 'Patient'),
        ('closed', 'Closed'),
    ]

    name = models.CharField(max_length=100,unique=True,help_text="Stage name (e.g. Contacted, Qualified)")
    slug = models.SlugField(max_length=100,unique=True,help_text="URL-friendly name (auto-generated)")
    stage_type = models.CharField(max_length=20,choices=STAGE_TYPES,default='lead',help_text="Stage type for filtering")
    color = models.CharField(max_length=7,default='#667eea',help_text="Hex color code for UI display")
    icon = models.CharField(max_length=50,blank=True,help_text="FontAwesome icon class (e.g. fas fa-phone)")
    description = models.TextField(blank=True,help_text="Stage description (what happens in this stage)")
    order = models.PositiveIntegerField(default=0,help_text="Display order in Kanban (lower numbers = left)")
    is_active = models.BooleanField(default=True,help_text="Is this stage active?")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lead Stage"
        verbose_name_plural = "Lead Stages"
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['stage_type']),
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Override save to auto-generate slug from name

        Process:
            1. Check if slug is empty
            2. Generate slug from name using slugify
            3. Save the model

        Example:
            name = "New Patient"
            slug = "new-patient"
        """
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)