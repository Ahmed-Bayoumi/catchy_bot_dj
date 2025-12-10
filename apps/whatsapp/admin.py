"""
This module provides admin interfaces for WhatsApp models:
- WoztellConfig: Manage API configurations
- Message: View and manage messages
- Channel: View and manage conversation channels
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import WoztellConfig, Message, Channel


@admin.register(WoztellConfig)
class WoztellConfigAdmin(admin.ModelAdmin):
    list_display = [
        'company',
        'channel_id',
        'status_badge',
        'created_at',
        'updated_at'
    ]
    list_filter = [
        'is_active',
        'created_at',
    ]
    search_fields = [
        'company__name',
        'channel_id',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'get_webhook_url_display',
    ]

    fieldsets = (
        (_('Company Information'), {
            'fields': ('company',)
        }),
        (_('API Credentials'), {
            'fields': ('api_key', 'api_secret', 'channel_id'),
            'description': _('Enter your Woztell API credentials from dashboard')
        }),
        (_('Webhook Configuration'), {
            'fields': ('webhook_secret', 'webhook_url', 'get_webhook_url_display'),
            'description': _('Configure webhook for receiving messages')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    ordering = ['-created_at']
    list_per_page = 25

    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 3px;">Active</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; '
            'padding: 3px 10px; border-radius: 3px;">Inactive</span>'
        )

    status_badge.short_description = _('Status')

    def get_webhook_url_display(self, obj):
        if obj.pk:
            url = obj.get_webhook_url()
            return format_html(
                '<input type="text" value="{}" readonly style="width: 100%; '
                'padding: 5px; border: 1px solid #ddd;" />',
                url
            )
        return _('Save first to generate webhook URL')

    get_webhook_url_display.short_description = _('Generated Webhook URL')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'direction_badge',
        'lead',
        'content_preview',
        'status_badge',
        'has_media_icon',
        'created_at',
    ]
    list_filter = [
        'direction',
        'status',
        'media_type',
        'created_at',
    ]
    search_fields = [
        'lead__name',
        'lead__phone',
        'content',
        'woztell_message_id',
    ]
    readonly_fields = [
        'lead',
        'user',
        'direction',
        'content',
        'media_url',
        'media_type',
        'status',
        'woztell_message_id',
        'error_message',
        'created_at',
        'updated_at',
    ]

    fieldsets = (
        (_('Message Information'), {
            'fields': ('lead', 'user', 'direction')
        }),
        (_('Content'), {
            'fields': ('content', 'media_url', 'media_type')
        }),
        (_('Status'), {
            'fields': ('status', 'error_message')
        }),
        (_('Integration'), {
            'fields': ('woztell_message_id',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    ordering = ['-created_at']
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        """Allow viewing but not editing"""
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def direction_badge(self, obj):
        if obj.direction == Message.DIRECTION_INCOMING:
            return format_html(
                '<span style="background-color: #17a2b8; color: white; '
                'padding: 3px 10px; border-radius: 3px;">← Incoming</span>'
            )
        return format_html(
            '<span style="background-color: #667eea; color: white; '
            'padding: 3px 10px; border-radius: 3px;">→ Outgoing</span>'
        )

    direction_badge.short_description = _('Direction')

    def content_preview(self, obj):
        if len(obj.content) > 50:
            return f"{obj.content[:50]}..."
        return obj.content

    content_preview.short_description = _('Content')

    def status_badge(self, obj):
        colors = {
            Message.STATUS_PENDING: '#ffc107',  # Yellow
            Message.STATUS_SENT: '#17a2b8',  # Blue
            Message.STATUS_DELIVERED: '#28a745',  # Green
            Message.STATUS_READ: '#28a745',  # Green
            Message.STATUS_FAILED: '#dc3545',  # Red
        }
        color = colors.get(obj.status, '#6c757d')  # Default gray

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_badge.short_description = _('Status')

    def has_media_icon(self, obj):
        if obj.has_media():
            icons = {
                Message.MEDIA_IMAGE: '🖼️',
                Message.MEDIA_VIDEO: '🎥',
                Message.MEDIA_DOCUMENT: '📄',
                Message.MEDIA_AUDIO: '🎵',
            }
            icon = icons.get(obj.media_type, '📎')
            return format_html(
                '<span title="{}">{}</span>',
                obj.get_media_type_display() if obj.media_type else 'Media',
                icon
            )
        return ''

    has_media_icon.short_description = _('Media')


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):

    list_display = [
        'id',
        'lead',
        'channel_type_badge',
        'unread_badge',
        'last_message_at',
        'status_badge',
        'created_at',
    ]
    list_filter = [
        'channel_type',
        'is_active',
        'created_at',
    ]
    search_fields = [
        'lead__name',
        'lead__phone',
        'channel_id',
    ]

    readonly_fields = [
        'company',
        'lead',
        'channel_type',
        'last_message_at',
        'created_at',
        'updated_at',
    ]

    fieldsets = (
        (_('Channel Information'), {
            'fields': ('company', 'lead', 'channel_type', 'channel_id')
        }),
        (_('Conversation Metadata'), {
            'fields': ('last_message_at', 'unread_count')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    ordering = ['-last_message_at']
    list_per_page = 50

    def has_add_permission(self, request):
        """Disable manual channel creation"""
        return False

    def channel_type_badge(self, obj):
        icons_colors = {
            Channel.TYPE_WHATSAPP: ('💬', '#25D366'),  # WhatsApp green
            Channel.TYPE_SMS: ('📱', '#667eea'),  # Blue
            Channel.TYPE_EMAIL: ('📧', '#dc3545'),  # Red
        }
        icon, color = icons_colors.get(obj.channel_type, ('📞', '#6c757d'))

        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{} {}</span>',
            color,
            icon,
            obj.get_channel_type_display()
        )

    channel_type_badge.short_description = _('Type')

    def unread_badge(self, obj):

        if obj.unread_count > 0:
            return format_html(
                '<span style="background-color: #dc3545; color: white; '
                'padding: 3px 8px; border-radius: 10px; font-weight: bold;">{}</span>',
                obj.unread_count
            )
        return format_html(
            '<span style="color: #28a745;">✓</span>'
        )

    unread_badge.short_description = _('Unread')

    def status_badge(self, obj):

        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 3px;">Active</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; '
            'padding: 3px 10px; border-radius: 3px;">Inactive</span>'
        )

    status_badge.short_description = _('Status')