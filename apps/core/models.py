from django.db import models
from django.utils.text import slugify
from django.core.validators import URLValidator
from django.utils.translation import gettext_lazy as _


class Company(models.Model):

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

        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_active_users_count(self):

        return self.users.filter(is_active=True).count()

    def get_total_leads_count(self):
        # TODO: Implement after Lead model is created
        # return self.leads.count()
        return 0

    def get_active_agents_count(self):

        return self.users.filter(is_active=True, role='agent').count()


class LeadSource(models.Model):

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

    name = models.CharField(max_length=100,unique=True,help_text="Stage name (e.g. Contacted, Qualified)")
    slug = models.SlugField(max_length=100,unique=True,help_text="URL-friendly name (auto-generated)")
    stage_type = models.CharField(max_length=20,choices=[('lead', 'Lead'),('patient', 'Patient'),('closed', 'Closed'),],
                                  default='lead',help_text="Stage type for filtering")

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

        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)