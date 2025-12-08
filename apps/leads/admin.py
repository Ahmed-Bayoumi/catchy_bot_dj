from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Lead, Note, Activity


class NoteInline(admin.TabularInline):

    model = Note
    extra = 1  # Show 1 empty form for adding new note
    readonly_fields = ['created_at']
    fields = ['user', 'content', 'created_at']
    classes = ['collapse']
    
    def get_queryset(self, request):
        """
        Override queryset to optimize database queries
        Use select_related to avoid N+1 queries
        """
        qs = super().get_queryset(request)
        return qs.select_related('user')


class ActivityInline(admin.TabularInline):

    model = Activity
    extra = 0  # No empty forms (activities are auto-created)
    readonly_fields = ['user', 'activity_type', 'description', 'created_at']
    fields = ['created_at', 'user', 'activity_type', 'description']
    classes = ['collapse']
    can_delete = False
    max_num = 10
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user').order_by('-created_at')[:10]


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    
    list_display = [
        'id',
        'name',
        'phone_display',
        'source_badge',
        'stage_badge',
        'status_badge',
        'priority_badge',
        'assigned_to_display',
        'created_at_display',
        'next_follow_up_display',
    ]
    
    list_filter = [
        'company',
        'source',
        'stage',
        'status',
        'priority',
        'assigned_to',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'phone',
        'email',
        'notes',
    ]
    
    ordering = ['-created_at']
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    fieldsets = [
        ('Basic Information', {
            'fields': ['company', 'name', 'phone', 'email']
        }),
        ('Classification', {
            'fields': ['source', 'stage', 'status', 'priority']
        }),
        ('Assignment & Follow-up', {
            'fields': ['assigned_to', 'next_follow_up']
        }),
        ('Additional Info', {
            'fields': ['notes', 'tags'],
            'classes': ['collapse'],
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    inlines = [NoteInline, ActivityInline]
    

    def phone_display(self, obj):
        """Display phone with icon"""
        return format_html(
            '<i class="fas fa-phone text-success"></i> {}',
            obj.phone
        )
    phone_display.short_description = 'Phone'
    
    def source_badge(self, obj):
        """Display source with colored badge"""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">'
            '<i class="{}"></i> {}</span>',
            obj.source.color,
            obj.source.icon,
            obj.source.name
        )
    source_badge.short_description = 'Source'
    
    def stage_badge(self, obj):
        """Display stage with colored badge"""
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">'
            '<i class="{}"></i> {}</span>',
            obj.stage.color,
            obj.stage.icon,
            obj.stage.name
        )
    stage_badge.short_description = 'Stage'
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'new': '#17a2b8',
            'contacted': '#ffc107',
            'qualified': '#28a745',
            'converted': '#667eea',
            'won': '#28a745',
            'lost': '#dc3545',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def priority_badge(self, obj):
        """Display priority with colored badge"""
        colors = {
            'low': '#6c757d',
            'medium': '#ffc107',
            'high': '#dc3545',
        }
        icons = {
            'low': 'fa-arrow-down',
            'medium': 'fa-minus',
            'high': 'fa-arrow-up',
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">'
            '<i class="fas {}"></i> {}</span>',
            colors.get(obj.priority, '#6c757d'),
            icons.get(obj.priority, 'fa-minus'),
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    def assigned_to_display(self, obj):
        """Display assigned user with avatar/initials"""
        if obj.assigned_to:
            return format_html(
                '<span style="background-color: #667eea; color: white; '
                'padding: 2px 6px; border-radius: 50%; font-size: 10px; '
                'margin-right: 5px;">{}</span> {}',
                obj.assigned_to.get_initials(),
                obj.assigned_to.get_full_name()
            )
        return format_html('<span style="color: #999;">Unassigned</span>')
    assigned_to_display.short_description = 'Assigned To'
    
    def created_at_display(self, obj):
        """Display creation date with relative time"""
        return format_html(
            '<span title="{}">{}</span>',
            obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            obj.time_since_created()
        )
    created_at_display.short_description = 'Created'
    
    def next_follow_up_display(self, obj):
        """Display next follow-up with color coding"""
        if not obj.next_follow_up:
            return format_html('<span style="color: #999;">-</span>')
        
        time_str = obj.time_until_follow_up()
        
        # Color based on urgency
        if time_str == "Overdue":
            color = '#dc3545'  # Red
        elif 'hour' in time_str or 'minute' in time_str:
            color = '#ffc107'  # Yellow
        else:
            color = '#28a745'  # Green
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            time_str
        )
    next_follow_up_display.short_description = 'Next Follow-up'
    
    # Custom actions
    
    actions = [
        'mark_as_contacted',
        'mark_as_qualified',
        'mark_as_lost',
        'set_high_priority',
        'set_medium_priority',
        'set_low_priority',
    ]
    
    def mark_as_contacted(self, request, queryset):
        count = queryset.update(status='contacted')

        for lead in queryset:
            Activity.objects.create(
                lead=lead,
                user=request.user,
                activity_type='status_changed',
                description='Status changed to "Contacted" (bulk action)'
            )
        
        self.message_user(request, f'Updated {count} leads to "Contacted"')
    mark_as_contacted.short_description = 'Mark as "Contacted"'
    
    def mark_as_qualified(self, request, queryset):
        count = queryset.update(status='qualified')
        
        for lead in queryset:
            Activity.objects.create(
                lead=lead,
                user=request.user,
                activity_type='status_changed',
                description='Status changed to "Qualified" (bulk action)'
            )
        
        self.message_user(request, f'Updated {count} leads to "Qualified"')
    mark_as_qualified.short_description = 'Mark as "Qualified"'
    
    def mark_as_lost(self, request, queryset):
        count = queryset.update(status='lost')
        
        for lead in queryset:
            Activity.objects.create(
                lead=lead,
                user=request.user,
                activity_type='status_changed',
                description='Status changed to "Lost" (bulk action)'
            )
        
        self.message_user(request, f'Updated {count} leads to "Lost"')
    mark_as_lost.short_description = 'Mark as "Lost"'
    
    def set_high_priority(self, request, queryset):
        count = queryset.update(priority='high')
        self.message_user(request, f'Set high priority for {count} leads')
    set_high_priority.short_description = 'Set High Priority'
    
    def set_medium_priority(self, request, queryset):
        count = queryset.update(priority='medium')
        self.message_user(request, f'Set medium priority for {count} leads')
    set_medium_priority.short_description = 'Set Medium Priority'
    
    def set_low_priority(self, request, queryset):
        count = queryset.update(priority='low')
        self.message_user(request, f'Set low priority for {count} leads')
    set_low_priority.short_description = 'Set Low Priority'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'company',
            'source',
            'stage',
            'assigned_to',
        )


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'lead',
        'user',
        'content_preview',
        'created_at'
    ]
    
    list_filter = [
        'created_at',
        'user'
    ]
    
    search_fields = [
        'content',
        'lead__name',
        'lead__phone'
    ]
    
    ordering = ['-created_at']
    list_per_page = 50
    readonly_fields = ['created_at']
    
    def content_preview(self, obj):
        """Show first 100 characters of content"""
        preview = obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
        return preview
    content_preview.short_description = 'Content'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('lead', 'user')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'lead',
        'user',
        'activity_type',
        'description',
        'created_at'
    ]
    
    list_filter = [
        'activity_type',
        'created_at',
        'user',
    ]
    
    search_fields = [
        'description',
        'lead__name',
        'lead__phone',
    ]
    
    ordering = ['-created_at']
    list_per_page = 100
    readonly_fields = ['lead', 'user', 'activity_type', 'description', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('lead', 'user')