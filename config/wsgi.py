# WSGI (Web Server Gateway Interface) configuration for production deployment

# WSGI is the standard interface between web servers and Python web apps
# Used by production servers like:
# - Gunicorn
# - uWSGI
# - Apache with mod_wsgi
#
# For WebSocket support, use ASGI instead (see asgi.py)
# ==============================================================================

import os
from django.core.wsgi import get_wsgi_application

# Set the default Django settings module
# Points to config/settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Create WSGI application
# This is what the production server will call
application = get_wsgi_application()


# ==============================================================================
# PRODUCTION DEPLOYMENT EXAMPLES
# ==============================================================================

# GUNICORN (Recommended)
# =====================
# Install: pip install gunicorn
# Run: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
#
# Docker command:
# docker compose exec web gunicorn config.wsgi:application --bind 0.0.0.0:8000
#
# systemd service file (/etc/systemd/system/catchybot.service):
# [Unit]
# Description=Catchy Bot CRM
# After=network.target
#
# [Service]
# User=www-data
# Group=www-data
# WorkingDirectory=/var/www/catchybot
# ExecStart=/var/www/catchybot/venv/bin/gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
#
# [Install]
# WantedBy=multi-user.target


# UWSGI (Alternative)
# ===================
# Install: pip install uwsgi
# Run: uwsgi --http :8000 --module config.wsgi:application
#
# uwsgi.ini configuration:
# [uwsgi]
# module = config.wsgi:application
# master = true
# processes = 4
# socket = /tmp/catchybot.sock
# chmod-socket = 664
# vacuum = true


# APACHE + MOD_WSGI (Alternative)
# ================================
# Install mod_wsgi: apt-get install libapache2-mod-wsgi-py3
#
# Apache configuration (/etc/apache2/sites-available/catchybot.conf):
# <VirtualHost *:80>
#     ServerName catchybot.com
#
#     WSGIDaemonProcess catchybot python-path=/var/www/catchybot python-home=/var/www/catchybot/venv
#     WSGIProcessGroup catchybot
#     WSGIScriptAlias / /var/www/catchybot/config/wsgi.py
#
#     <Directory /var/www/catchybot/config>
#         <Files wsgi.py>
#             Require all granted
#         </Files>
#     </Directory>
#
#     Alias /static/ /var/www/catchybot/staticfiles/
#     Alias /media/ /var/www/catchybot/media/
# </VirtualHost>


# ==============================================================================
# NOTES
# ==============================================================================
#
# 1. WSGI is synchronous - doesn't support WebSocket
#    For WebSocket (chat), use ASGI (see asgi.py)
#
# 2. Always run with multiple workers in production
#    Rule of thumb: (2 x CPU cores) + 1
#
# 3. Use a reverse proxy (Nginx) in front of Gunicorn
#    Nginx handles static files, SSL, load balancing
#
# 4. Set environment variables in production:
#    - DEBUG=False
#    - SECRET_KEY=<random-value>
#    - ALLOWED_HOSTS=yourdomain.com
#
# ==============================================================================