from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# Main URL Configuration
# Routes all requests to appropriate apps

urlpatterns = [
    # ========== Django Admin Panel ==========
    # URL: /admin/
    # Purpose: Django's built-in admin interface
    # Access: Superusers only
    path('admin/', admin.site.urls),

    # ========== Accounts App ==========
    # URL: /accounts/...
    # Purpose: User authentication (login, logout, profile)
    # Includes:
    #   - /accounts/login/ → Login page
    #   - /accounts/logout/ → Logout action
    #   - /accounts/profile/ → User profile page
    path('accounts/', include('apps.accounts.urls')),

    # ========== Core App (Dashboard) ==========
    # URL: /dashboard/...
    # Purpose: Main dashboard and company settings
    # Includes:
    #   - /dashboard/ → Main dashboard
    #   - /dashboard/settings/company/ → Company settings
    path('dashboard/', include('apps.core.urls')),

    # ========== Root Redirect ==========
    # URL: /
    # Purpose: Smart redirect based on authentication
    # Logic:
    #   - If authenticated → Redirect to dashboard
    #   - If not authenticated → Redirect to login
    #
    # This ensures users always land on the right page
    path('',
         lambda request: redirect('core:dashboard') if request.user.is_authenticated else redirect('accounts:login')),
]

# ========== Media Files (Development Only) ==========
# Serves uploaded files in development mode
# In production, use nginx/apache to serve media files
if settings.DEBUG:
    # Media files (user uploads: logos, avatars, etc.)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Static files (CSS, JS, images)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)