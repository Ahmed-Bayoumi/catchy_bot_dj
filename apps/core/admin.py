from django.contrib import admin
from django.utils.html import format_html
from .models import Company, LeadSource, LeadStage


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):

    list_display = [
        'name',
        'contact_info',
        'status_badge',
        'users_count',
        'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'email', 'phone']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'logo', 'description')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email', 'website', 'address')
        }),
        ('Settings', {
            'fields': ('working_hours', 'timezone')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def contact_info(self, obj):

        html = f'<div style="line-height: 1.5;">'
        if obj.phone:
            html += f'📞 {obj.phone}<br>'
        if obj.email:
            html += f'📧 {obj.email}'
        html += '</div>'
        return format_html(html) if (obj.phone or obj.email) else '-'

    contact_info.short_description = 'Contact'

    def status_badge(self, obj):

        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 3px; font-size: 11px;">'
                'Active</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">'
            'Inactive</span>'
        )

    status_badge.short_description = 'Status'

    def users_count(self, obj):

        count = obj.get_active_users_count()
        return format_html(
            '<span style="color: #667eea; font-weight: bold;">{} users</span>',
            count
        )

    users_count.short_description = 'Users'


@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):

    list_display = [
        'order',
        'name_with_icon',
        'color_preview',
        'status_badge',
        'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    ordering = ['order', 'name']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Visual Settings', {
            'fields': ('icon', 'color', 'order'),
            'description': 'Icon: FontAwesome class (e.g. fab fa-whatsapp), Color: Hex code (e.g. #25D366)'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def name_with_icon(self, obj):

        return format_html(
            '<i class="{}" style="color: {}; margin-right: 8px;"></i> {}',
            obj.icon,
            obj.color,
            obj.name
        )

    name_with_icon.short_description = 'Source'

    def color_preview(self, obj):

        return format_html(
            '<div style="width: 40px; height: 20px; background-color: {}; '
            'border-radius: 3px; border: 1px solid #ddd;"></div>',
            obj.color
        )

    color_preview.short_description = 'Color'

    def status_badge(self, obj):

        if obj.is_active:
            return format_html(
                '<span style="background-color: #28a745; color: white; '
                'padding: 3px 10px; border-radius: 3px; font-size: 11px;">'
                '✓ Active</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">'
            '✗ Inactive</span>'
        )

    status_badge.short_description = 'Status'


@admin.register(LeadStage)
class LeadStageAdmin(admin.ModelAdmin):

    list_display = [
        'order',
        'name_with_icon',
        'stage_type_badge',
        'color_preview',
        'status_badge'
    ]
    list_filter = ['stage_type', 'is_active', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description')
        }),
        ('Settings', {
            'fields': ('stage_type', 'order'),
            'description': 'Order determines position in Kanban board (lower = left)'
        }),
        ('Visual Settings', {
            'fields': ('icon', 'color'),
            'description': 'Icon: FontAwesome class (e.g. fas fa-phone), Color: Hex code (e.g. #ffc107)'
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    def name_with_icon(self, obj):
        icon_html = ''
        if obj.icon:
            icon_html = f'<i class="{obj.icon}" style="color: {obj.color}; margin-right: 8px;"></i>'
        return format_html(
            '{} <strong>{}</strong>',
            icon_html,
            obj.name
        )

    name_with_icon.short_description = 'Stage'

    def stage_type_badge(self, obj):

        colors = {
            'lead': '#17a2b8',  #  blue
            'patient': '#28a745',  #  green
            'closed': '#6c757d',  #  gray
        }
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.stage_type, '#6c757d'),
            obj.get_stage_type_display()
        )

    stage_type_badge.short_description = 'Type'

    def color_preview(self, obj):
        return format_html(
            '<div style="width: 40px; height: 20px; background-color: {}; '
            'border-radius: 3px; border: 1px solid #ddd;"></div>',
            obj.color
        )

    color_preview.short_description = 'Color'

    def status_badge(self, obj):

        if obj.is_active:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">● Active</span>'
            )
        return format_html(
            '<span style="color: #dc3545; font-weight: bold;">● Inactive</span>'
        )

    status_badge.short_description = 'Status'