from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

# Main URL Configuration
# Routes all requests to appropriate apps

urlpatterns = [

    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.core.urls')),
    path('', lambda request: redirect('core:dashboard') if request.user.is_authenticated else redirect('accounts:login')),
    path('leads/', include('apps.leads.urls')),
    path('api/', include('apps.whatsapp.urls')),


]

if settings.DEBUG:
    # Media files (user uploads: logos, avatars, etc.)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    # Static files (CSS, JS, images)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)