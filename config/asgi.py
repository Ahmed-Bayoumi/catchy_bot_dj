# ASGI (Asynchronous Server Gateway Interface) configuration

# ASGI is the async successor to WSGI
# Required for:
# - WebSocket connections (real-time chat)
# - HTTP/2 support
# - Long-polling
# - Server-sent events
#
# Production servers:
# - Daphne (Django Channels official server)
# - Uvicorn
# - Hypercorn
# ==============================================================================

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Initialize Django ASGI application early
# This ensures the AppRegistry is populated before importing code that may import ORM models
django_asgi_app = get_asgi_application()

# Import routing after Django setup
# This prevents "Apps aren't loaded yet" error
#from apps.chat.routing import websocket_urlpatterns


# ASGI APPLICATION

# ProtocolTypeRouter dispatches connections based on protocol type
# - 'http': Regular HTTP requests → Django views
# - 'websocket': WebSocket connections → Channels consumers
application = ProtocolTypeRouter({
    # Handle traditional HTTP requests with Django
    'http': django_asgi_app,

    # Handle WebSocket connections
    #'websocket': AuthMiddlewareStack(
        # AuthMiddlewareStack adds Django's authentication to WebSocket
        # This gives access to request.user in WebSocket consumers
     #   URLRouter(
            # Route WebSocket URLs to appropriate consumers
            # Defined in apps/chat/routing.py
      #      websocket_urlpatterns
       # )
    #),
})

# ==============================================================================
# PRODUCTION DEPLOYMENT WITH DAPHNE
# ==============================================================================

# DAPHNE (Recommended for Django Channels)
# =========================================
# Install: pip install daphne
# Run: daphne config.asgi:application --bind 0.0.0.0 --port 8000
#
# Docker command:
# docker compose exec web daphne config.asgi:application --bind 0.0.0.0 --port 8000
#
# systemd service file (/etc/systemd/system/catchybot-asgi.service):
# [Unit]
# Description=Catchy Bot CRM ASGI Server
# After=network.target
#
# [Service]
# User=www-data
# Group=www-data
# WorkingDirectory=/var/www/catchybot
# ExecStart=/var/www/catchybot/venv/bin/daphne config.asgi:application --bind 0.0.0.0 --port 8000
# Restart=always
#
# [Install]
# WantedBy=multi-user.target


# UVICORN (Alternative - Very Fast)
# ==================================
# Install: pip install uvicorn
# Run: uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --workers 4
#
# With auto-reload (development):
# uvicorn config.asgi:application --reload


# NGINX CONFIGURATION (Reverse Proxy)
# ====================================
# Nginx handles:
# - SSL/TLS termination
# - Static file serving
# - Load balancing
# - WebSocket proxying
#
# /etc/nginx/sites-available/catchybot:
#
# upstream catchybot {
#     server 127.0.0.1:8000;
# }
#
# server {
#     listen 80;
#     server_name catchybot.com www.catchybot.com;
#
#     # Redirect to HTTPS
#     return 301 https://$server_name$request_uri;
# }
#
# server {
#     listen 443 ssl http2;
#     server_name catchybot.com www.catchybot.com;
#
#     # SSL certificates
#     ssl_certificate /etc/letsencrypt/live/catchybot.com/fullchain.pem;
#     ssl_certificate_key /etc/letsencrypt/live/catchybot.com/privkey.pem;
#
#     # Static files
#     location /static/ {
#         alias /var/www/catchybot/staticfiles/;
#         expires 30d;
#     }
#
#     # Media files
#     location /media/ {
#         alias /var/www/catchybot/media/;
#         expires 30d;
#     }
#
#     # WebSocket support
#     location /ws/ {
#         proxy_pass http://catchybot;
#         proxy_http_version 1.1;
#         proxy_set_header Upgrade $http_upgrade;
#         proxy_set_header Connection "upgrade";
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header X-Forwarded-Proto $scheme;
#         proxy_redirect off;
#     }
#
#     # Regular HTTP requests
#     location / {
#         proxy_pass http://catchybot;
#         proxy_set_header Host $host;
#         proxy_set_header X-Real-IP $remote_addr;
#         proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
#         proxy_set_header X-Forwarded-Proto $scheme;
#     }
# }


# ==============================================================================
# WEBSOCKET URL PATTERNS STRUCTURE
# ==============================================================================

# WebSocket URLs are defined in apps/chat/routing.py
# Example structure:
#
# from django.urls import path
# from . import consumers
#
# websocket_urlpatterns = [
#     path('ws/chat/<int:channel_id>/', consumers.ChatConsumer.as_asgi()),
#     path('ws/notifications/', consumers.NotificationConsumer.as_asgi()),
# ]
#
# Usage in JavaScript:
# const socket = new WebSocket('ws://localhost:8008/ws/chat/123/');


# ==============================================================================
# SCALING WITH REDIS
# ==============================================================================

# When running multiple Daphne instances, use Redis as channel layer
# This allows WebSocket messages to be shared across servers
#
# settings.py configuration:
# CHANNEL_LAYERS = {
#     'default': {
#         'BACKEND': 'channels_redis.core.RedisChannelLayer',
#         'CONFIG': {
#             'hosts': [('redis', 6379)],
#         },
#     },
# }
#
# Docker Compose setup:
# - Multiple Daphne containers (web1, web2, web3)
# - Single Redis container (shared channel layer)
# - Nginx load balancer in front


# ==============================================================================
# MONITORING & LOGGING
# ==============================================================================

# Monitor ASGI servers in production:
# 1. Use systemd for process management
# 2. Set up health checks
# 3. Monitor memory/CPU usage
# 4. Log WebSocket connections/disconnections
# 5. Track message throughput
#
# Tools:
# - Prometheus + Grafana (metrics)
# - Sentry (error tracking)
# - ELK Stack (logs)


# ==============================================================================
# NOTES
# ==============================================================================
#
# 1. ASGI supports both HTTP and WebSocket
#    Use ASGI for full-stack deployment (not WSGI + ASGI)
#
# 2. Always use TLS/SSL (wss://) for WebSocket in production
#    Never use ws:// (unencrypted)
#
# 3. Set proper timeouts for WebSocket connections
#    Default: 86400 seconds (24 hours)
#
# 4. Implement connection limiting to prevent DoS
#    Use rate limiting on WebSocket connections
#
# 5. Test with multiple clients before production
#    Tools: WebSocket King, wscat, Artillery
#
# ==============================================================================