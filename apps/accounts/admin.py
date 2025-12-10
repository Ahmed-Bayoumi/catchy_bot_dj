from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from .models import User, UserProfile


# USER PROFILE INLINE (Edit profile inside user form)
class UserProfileInline(admin.StackedInline):

    model = UserProfile

    # Show only 1 profile (since it's OneToOne relationship)
    can_delete = False
    verbose_name = _('User Profile')
    verbose_name_plural = _('User Profile')

    fk_name = "user"
    extra = 0
    max_num = 1


    # Fieldsets for better organization (with collapse)
    fieldsets = (
        (_('Personal Information'), {
            'fields': ('bio', 'date_of_birth', 'address', 'city', 'country'),
            'classes': ('wide',),
        }),
        (_('Notification Settings'), {
            'fields': ('email_notifications', 'sms_notifications'),
            'classes': ('collapse',),  # Collapsed by default
        }),
         (_('Preferences'), {
             'fields': ('theme',
        #     'language'
                             ),
             'classes': ('collapse',),
         }),
        (_('Social Links'), {
            'fields': ('linkedin_url', 'twitter_url'),
            'classes': ('collapse',),
        }),
    )



# CUSTOM USER ADMIN
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'email',
        'get_full_name_display',
        'company',
        'role_badge',
        'is_active_badge',
        'performance_display',
        'login_count',
        'date_joined',
    )

    # Fields that can be clicked to open edit form
    list_display_links = ('email', 'get_full_name_display')

    # Filters in right sidebar
    list_filter = (
        'role',
        'is_active',
        'is_staff',
        'is_superuser',
        'company',
        'date_joined',
    )
    search_fields = (
        'email',
        'first_name',
        'last_name',
        'phone',
        'company__name',
    )

    ordering = ('-date_joined',)
    list_per_page = 25

    # Enable "select all" across pages
    list_select_related = (
        'company',
        'profile',)


    fieldsets = (
        # Basic Information
        (_('Login Credentials'), {
            'fields': ('email', 'password'),
            'classes': ('wide',),
            'description': _('Email is used for login. Password is stored encrypted.')
        }),

        # Personal Information
        (_('Personal Information'), {
            'fields': ('first_name', 'last_name', 'phone', 'avatar', 'job_title', 'department'),
            'classes': ('wide',),
        }),

        #Company & Role
        (_('Company & Role'), {
            'fields': ('company', 'role'),
            'classes': ('wide',),
            'description': _('Company association and user role (admin or agent)')
        }),

        # Performance Metrics (read-only)
        (_('Performance Metrics'), {
            'fields': (
                'total_leads_assigned',
                'total_leads_converted',
                'total_leads_won',
                'get_conversion_rate_display',
                'get_win_rate_display',
            ),
            'classes': ('collapse',),  # Collapsed by default
            'description': _('Automatically calculated based on lead activities')
        }),

        # Permissions
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),

        # Activity Tracking
        (_('Activity Tracking'), {
            'fields': ('login_count', 'last_login_ip', 'date_joined', 'last_login'),
            'classes': ('collapse',),
        }),
    )

    # Fields shown when creating NEW user
    add_fieldsets = (
        (_('Login Credentials'), {
            'fields': ('email', 'password1', 'password2'),
            'classes': ('wide',),
        }),
        (_('Personal Information'), {
            'fields': ('first_name', 'last_name', 'phone'),
            'classes': ('wide',),
        }),
        (_('Company & Role'), {
            'fields': ('role',),
            'classes': ('wide',),
        }),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff'),
        }),
    )

    readonly_fields = (
        'date_joined',
        'last_login',
        'login_count',
        'last_login_ip',
        'get_conversion_rate_display',
        'get_win_rate_display',
    )

    # Include profile inline
    inlines = [UserProfileInline]

    # CUSTOM DISPLAY METHODS
    def get_full_name_display(self, obj):
        return obj.get_full_name()

    get_full_name_display.short_description = _('Full Name')
    get_full_name_display.admin_order_field = 'first_name'

    def role_badge(self, obj):

        if obj.role == 'admin':
            color = '#28a745'  # Green
            icon = '⭐'
        else:
            color = '#007bff'  # Blue
            icon = '👤'

        return format_html(
            '<span style="background: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{} {}</span>',
            color, icon, obj.get_role_display()
        )

    role_badge.short_description = _('Role')
    role_badge.admin_order_field = 'role'

    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-size: 11px;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-size: 11px;">✗ Inactive</span>'
            )

    is_active_badge.short_description = _('Status')
    is_active_badge.admin_order_field = 'is_active'

    def performance_display(self, obj):
        score = obj.get_performance_score()
        try:
            score = float(score)
        except:
            score = 0

        # Color based on performance
        if score >= 70:
            color = '#28a745'  # Green (excellent)
        elif score >= 50:
            color = '#ffc107'  # Yellow (good)
        else:
            color = '#dc3545'  # Red (needs improvement)

        score_text = f"{int(score)}%"

        return format_html(
            '<div style="width: 100px; background: #f0f0f0; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; background: {}; padding: 2px 5px; color: white; '
            'font-size: 10px; text-align: center;">{}</div>'
            '</div>',
            score, color, score_text
        )

    performance_display.short_description = _('Performance')

    def get_conversion_rate_display(self, obj):
        rate = obj.get_conversion_rate()
        return f"{rate:.1f}% ({obj.total_leads_converted}/{obj.total_leads_assigned})"

    get_conversion_rate_display.short_description = _('Conversion Rate')

    def get_win_rate_display(self, obj):
        rate = obj.get_win_rate()
        return f"{rate:.1f}% ({obj.total_leads_won}/{obj.total_leads_assigned})"

    get_win_rate_display.short_description = _('Win Rate')

    # CUSTOM ACTIONS
    actions = ['activate_users', 'deactivate_users', 'reset_password_action']

    def activate_users(self, request, queryset):
        """
        Bulk action: Activate selected users
        """
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            _(f'{updated} user(s) were successfully activated.'),
            level='success'
        )

    activate_users.short_description = _('Activate selected users')

    def deactivate_users(self, request, queryset):
        """
        Bulk action: Deactivate selected users

        Note: Cannot deactivate superusers (safety measure)
        """
        # Exclude superusers
        queryset = queryset.filter(is_superuser=False)
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            _(f'{updated} user(s) were successfully deactivated.'),
            level='success'
        )

    deactivate_users.short_description = _('Deactivate selected users')

    def reset_password_action(self, request, queryset):
        """
        Bulk action: Reset password for selected users

        Sends password reset email to each user
        """
        # This will be implemented when email is set up
        self.message_user(
            request,
            _('Password reset emails will be sent (feature coming soon).'),
            level='warning'
        )

    reset_password_action.short_description = _('Send password reset email')

    # CUSTOM QUERYSET (for performance)
    def get_queryset(self, request):

        queryset = super().get_queryset(request)
        queryset = queryset.select_related('company', 'profile')
        return queryset


    # PERMISSIONS
    def has_delete_permission(self, request, obj=None):
        if obj and obj == request.user:
            return False  # Cannot delete yourself

        if obj and obj.is_superuser and not request.user.is_superuser:
            return False  # Cannot delete superuser unless you are one

        return super().has_delete_permission(request, obj)


# USER PROFILE ADMIN (Standalone)
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'city',
        'country',
        'email_notifications',
        'theme',
        # 'language',
        'profile_completion',
    )

    list_filter = (
        'country',
        'city',
        'email_notifications',
        'sms_notifications',
        'theme',
        # 'language',
    )

    search_fields = (
        'user__email',
        'user__first_name',
        'user__last_name',
        'bio',
        'city',
    )

    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (_('User'), {
            'fields': ('user',),
        }),
        (_('Personal Information'), {
            'fields': ('bio', 'date_of_birth', 'address', 'city', 'country'),
        }),
        (_('Notification Settings'), {
            'fields': ('email_notifications', 'sms_notifications'),
        }),
        # (_('Preferences'), {
        #     'fields': ('theme', 'language'),
        # }),
        (_('Social Links'), {
            'fields': ('linkedin_url', 'twitter_url'),
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def profile_completion(self, obj):

        percentage = obj.get_completion_percentage()

        if percentage == 100:
            color = '#28a745'  # Green
        elif percentage >= 70:
            color = '#17a2b8'  # Blue
        elif percentage >= 40:
            color = '#ffc107'  # Yellow
        else:
            color = '#dc3545'  # Red

        return format_html(
            '<div style="width: 100px; background: #f0f0f0; border-radius: 3px; overflow: hidden;">'
            '<div style="width: {}%; background: {}; padding: 2px 5px; color: white; '
            'font-size: 10px; text-align: center;">{}%</div>'
            '</div>',
            percentage, color, percentage
        )

    profile_completion.short_description = _('Completion')


# ADMIN SITE CUSTOMIZATION
# Customize admin site header and title
admin.site.site_header = _('Catchy Bot Administration')
admin.site.site_title = _('Catchy Bot')
admin.site.index_title = _('Welcome to Catchy Bot Admin Panel')


