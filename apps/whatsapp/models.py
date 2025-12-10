"""
This module contains models for WhatsApp integration via Woztell API:
- WoztellConfig: Stores API credentials per company
- Message: Stores all incoming/outgoing messages
- Channel: Represents a conversation channel with a lead
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from apps.core.models import Company
from apps.leads.models import Lead
from django.conf import settings

User = get_user_model()


class WoztellConfig(models.Model):

    company = models.OneToOneField(Company,on_delete=models.CASCADE,related_name='woztell_config',verbose_name=_('Company'),help_text=_('Company that owns this configuration'))

    api_key = models.CharField(max_length=255,verbose_name=_('API Key'),help_text=_('Woztell API key for authentication'))
    api_secret = models.CharField(max_length=255,verbose_name=_('API Secret'),help_text=_('Woztell API secret key'))
    channel_id = models.CharField(max_length=100,verbose_name=_('Channel ID'),help_text=_('WhatsApp Business channel ID from Woztell'))
    webhook_secret = models.CharField(max_length=255,verbose_name=_('Webhook Secret'),help_text=_('Secret key to validate incoming webhooks'))
    webhook_url = models.URLField(max_length=500,blank=True,null=True,verbose_name=_('Webhook URL'),help_text=_('Full webhook URL (for reference)'))

    is_active = models.BooleanField(default=True,verbose_name=_('Is Active'),help_text=_('Whether this configuration is active'))
    created_at = models.DateTimeField(auto_now_add=True,verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True,verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Woztell Configuration')
        verbose_name_plural = _('Woztell Configurations')
        ordering = ['-created_at']

    def __str__(self):
        return f"Woztell Config - {self.company.name}"

    def get_webhook_url(self):
        base_url = settings.SITE_URL
        return f"{base_url}/api/webhook/woztell/{self.webhook_secret}/"


class Message(models.Model):

    lead = models.ForeignKey(Lead,on_delete=models.CASCADE,related_name='messages',verbose_name=_('Lead'),help_text=_('Lead associated with this message'))
    user = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name='sent_messages',verbose_name=_('User'),help_text=_('User who sent this message (null for incoming)'))

    DIRECTION_INCOMING = 'incoming'
    DIRECTION_OUTGOING = 'outgoing'
    DIRECTION_CHOICES = [(DIRECTION_INCOMING, _('Incoming')),(DIRECTION_OUTGOING, _('Outgoing')),]

    direction = models.CharField(max_length=10,choices=DIRECTION_CHOICES,verbose_name=_('Direction'),help_text=_('Message direction (incoming or outgoing)'))
    content = models.TextField(verbose_name=_('Content'),help_text=_('Text content of the message'))
    media_url = models.URLField(max_length=500,blank=True,null=True,verbose_name=_('Media URL'),help_text=_('URL to media file (if any)'))

    MEDIA_IMAGE = 'image'
    MEDIA_VIDEO = 'video'
    MEDIA_DOCUMENT = 'document'
    MEDIA_AUDIO = 'audio'
    MEDIA_CHOICES = [(MEDIA_IMAGE, _('Image')),(MEDIA_VIDEO, _('Video')),(MEDIA_DOCUMENT, _('Document')),(MEDIA_AUDIO, _('Audio')),]

    media_type = models.CharField(max_length=20,choices=MEDIA_CHOICES,blank=True,null=True,verbose_name=_('Media Type'),help_text=_('Type of media attachment'))

    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_DELIVERED = 'delivered'
    STATUS_READ = 'read'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [(STATUS_PENDING, _('Pending')),(STATUS_SENT, _('Sent')),
                      (STATUS_DELIVERED, _('Delivered')),(STATUS_READ, _('Read')),
                      (STATUS_FAILED, _('Failed')),]

    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default=STATUS_PENDING,verbose_name=_('Status'),help_text=_('Delivery status of the message'))

    woztell_message_id = models.CharField(max_length=255,blank=True,null=True,verbose_name=_('Woztell Message ID'),help_text=_('Message ID from Woztell API'))

    error_message = models.TextField(blank=True,null=True,verbose_name=_('Error Message'),help_text=_('Error message if sending failed'))
    created_at = models.DateTimeField(auto_now_add=True,verbose_name=_('Created At'),db_index=True)
    updated_at = models.DateTimeField(auto_now=True,verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Message')
        verbose_name_plural = _('Messages')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['lead', 'direction', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        direction_icon = '→' if self.direction == self.DIRECTION_OUTGOING else '←'
        content_preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{direction_icon} {self.lead.name}: {content_preview}"

    def is_incoming(self):
        return self.direction == self.DIRECTION_INCOMING

    def is_outgoing(self):
        return self.direction == self.DIRECTION_OUTGOING

    def has_media(self):
        return bool(self.media_url)

    def mark_as_sent(self, woztell_message_id=None):
        self.status = self.STATUS_SENT
        if woztell_message_id:
            self.woztell_message_id = woztell_message_id
        self.save(update_fields=['status', 'woztell_message_id', 'updated_at'])

    def mark_as_delivered(self):
        self.status = self.STATUS_DELIVERED
        self.save(update_fields=['status', 'updated_at'])

    def mark_as_read(self):
        self.status = self.STATUS_READ
        self.save(update_fields=['status', 'updated_at'])

    def mark_as_failed(self, error_message):
        self.status = self.STATUS_FAILED
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])


class Channel(models.Model):

    company = models.ForeignKey(Company,on_delete=models.CASCADE,related_name='channels',verbose_name=_('Company'))
    lead = models.ForeignKey(Lead,on_delete=models.CASCADE,related_name='channels',verbose_name=_('Lead'),help_text=_('Lead associated with this channel'))

    TYPE_WHATSAPP = 'whatsapp'
    TYPE_SMS = 'sms'
    TYPE_EMAIL = 'email'
    TYPE_CHOICES = [(TYPE_WHATSAPP, _('WhatsApp')),(TYPE_EMAIL, _('Email')),(TYPE_SMS, _('SMS')),]

    channel_type = models.CharField(max_length=20,choices=TYPE_CHOICES,default=TYPE_WHATSAPP,verbose_name=_('Channel Type'),help_text=_('Type of communication channel'))
    channel_id = models.CharField(max_length=255,blank=True,null=True,verbose_name=_('Channel ID'),help_text=_('External channel ID from provider'))

    last_message_at = models.DateTimeField(blank=True,null=True,verbose_name=_('Last Message At'),help_text=_('Timestamp of last message in this channel'),db_index=True)
    unread_count = models.PositiveIntegerField(default=0,verbose_name=_('Unread Count'),help_text=_('Number of unread messages'))

    is_active = models.BooleanField(default=True,verbose_name=_('Is Active'),help_text=_('Whether this channel is active'))

    created_at = models.DateTimeField(auto_now_add=True,verbose_name=_('Created At'))
    updated_at = models.DateTimeField(auto_now=True,verbose_name=_('Updated At'))

    class Meta:
        verbose_name = _('Channel')
        verbose_name_plural = _('Channels')
        ordering = ['-last_message_at']
        unique_together = [['lead', 'channel_type']]
        indexes = [
            models.Index(fields=['company', 'is_active', '-last_message_at']),
        ]

    def __str__(self):
        return f"{self.get_channel_type_display()} - {self.lead.name}"

    def increment_unread(self):
        self.unread_count += 1
        self.save(update_fields=['unread_count', 'updated_at'])

    def mark_as_read(self):
        self.unread_count = 0
        self.save(update_fields=['unread_count', 'updated_at'])

    def update_last_message(self):
        from django.utils import timezone
        self.last_message_at = timezone.now()
        self.save(update_fields=['last_message_at', 'updated_at'])