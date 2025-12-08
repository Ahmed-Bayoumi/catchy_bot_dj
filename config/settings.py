import os
from pathlib import Path
from decouple import config


# BASE DIRECTORY
# Build paths inside the project like this: BASE_DIR / 'subdir'
# BASE_DIR points to the project root (where manage.py is)
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY SETTINGS

# SECURITY WARNING: keep the secret key used in production secret!
# This key is used for:
# - Cryptographic signing (sessions, cookies, passwords)
# - Generating tokens
# - CSRF protection
# Generate new key: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
SECRET_KEY = config('SECRET_KEY', default='django-insecure-CHANGE-THIS-IN-PRODUCTION')

# SECURITY WARNING: don't run with debug turned on in production!
# Debug mode shows detailed error pages with sensitive information
# Always set to False in production!
DEBUG = config('DEBUG', default=True, cast=bool)

# Allowed hosts (domains that can access this application)
# Security measure to prevent host header attacks
# Format: 'domain.com,www.domain.com,api.domain.com'
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,0.0.0.0').split(',')


# INSTALLED APPS

# Django apps and third-party packages used in this project
# Order matters! Some apps depend on others
INSTALLED_APPS = [
    # Django Channels (must be before django.contrib.staticfiles)
    'daphne',  # ASGI server for WebSocket support

    # Django built-in apps
    'django.contrib.admin',  # Admin interface
    'django.contrib.auth',  # Authentication framework
    'django.contrib.contenttypes',  # Content types framework
    'django.contrib.sessions',  # Session framework
    'django.contrib.messages',  # Messaging framework
    'django.contrib.staticfiles',  # Static files management

    # Third-party apps
    'rest_framework',  # Django REST Framework (API)
    'corsheaders',  # CORS headers support
    'crispy_forms',  # Better form rendering
    'crispy_bootstrap5',  # Bootstrap 5 template pack
    'channels',  # WebSocket support
    'taggit',  # Tags for categorizing leads

    # Our custom apps
    # IMPORTANT: accounts must be first (custom user model)
    'apps.accounts',  # User management & authentication
    'apps.core',  # Core functionality (Company, etc.)
    'apps.leads',  # Lead management
 #   'apps.whatsapp',  # WhatsApp integration
 #   'apps.chat',  # Real-time chat
 #   'apps.appointments',  # Appointment scheduling
 #   'apps.contacts',  # Contact management
    # 'apps.reports',  # Reports & analytics
]


# MIDDLEWARE

# Middleware components (order matters!)
# Each request passes through these in order (top to bottom)
# Each response passes through in reverse order (bottom to top)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',  # Security enhancements
    'django.contrib.sessions.middleware.SessionMiddleware',  # Session support
    'corsheaders.middleware.CorsMiddleware',  # CORS support (must be before CommonMiddleware)
    'django.middleware.common.CommonMiddleware',  # Common utilities
    'django.middleware.csrf.CsrfViewMiddleware',  # CSRF protection
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Authentication
    'django.contrib.messages.middleware.MessageMiddleware',  # Messages framework
    'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Clickjacking protection
    # Custom middleware (will be added later)
    # 'apps.core.middleware.TenantMiddleware',            # Multi-tenancy support
]


# URL CONFIGURATION

# Root URL configuration file
ROOT_URLCONF = 'config.urls'


# TEMPLATES
# Template engine configuration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

        # Directories where Django looks for templates
        'DIRS': [
            BASE_DIR / 'templates',  # Global templates directory
        ],

        # Look for templates inside each app's templates/ directory
        'APP_DIRS': True,

        # Context processors: variables available in all templates
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',  # Debug info
                'django.template.context_processors.request',  # Request object
                'django.contrib.auth.context_processors.auth',  # User object
                'django.contrib.messages.context_processors.messages',  # Messages
                # Custom context processors (will be added later)
                # 'apps.core.context_processors.global_settings',  # Global variables
            ],
        },
    },
]


# ASGI/WSGI APPLICATION

# ASGI application (for async/WebSocket support)
# Used by Daphne and Django Channels
ASGI_APPLICATION = 'config.asgi.application'

# WSGI application (for traditional HTTP)
# Used by Gunicorn, uWSGI, etc.
WSGI_APPLICATION = 'config.wsgi.application'


# DATABASE

# Database configuration
# We use PostgreSQL (production-grade database)
# Connection string format: postgresql://user:password@host:port/database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='catchybot_db'),
        'USER': config('DB_USER', default='catchybot_user'),
        'PASSWORD': config('DB_PASSWORD', default='catchybot_pass'),
        'HOST': config('DB_HOST', default='db'),  # 'db' is Docker service name
        'PORT': config('DB_PORT', default='5432'),

        # Connection pool settings (for better performance)
        'CONN_MAX_AGE': 600,  # Keep connection open for 10 minutes

        # Additional options
        'OPTIONS': {
            'connect_timeout': 10,  # Timeout if connection fails
        }
    }
}


# AUTHENTICATION

# Custom user model (instead of Django's default User)
# IMPORTANT: This MUST be set before first migration!
# Points to our custom User model in accounts app
AUTH_USER_MODEL = 'accounts.User'

# Password validation
# Ensures users create strong passwords
# AUTH_PASSWORD_VALIDATORS = [           #########################################
#     {
#         'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
#         # Prevents password similar to username/email
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
#         'OPTIONS': {
#             'min_length': 8,  # Minimum 8 characters
#         }
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
#         # Prevents common passwords (123456, password, etc.)
#     },
#     {
#         'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
#         # Prevents all-numeric passwords
#     },
# ]

# Login/Logout URLs
LOGIN_URL = '/accounts/login/'  # Redirect here if not authenticated
LOGIN_REDIRECT_URL = '/dashboard/'  # Redirect after successful login
LOGOUT_REDIRECT_URL = '/accounts/login/'  # Redirect after logout


# INTERNATIONALIZATION

# Language code for this installation
# 'en-us' = English, 'ar' = Arabic
LANGUAGE_CODE = 'en-us'

# Time zone for this installation
# List: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
TIME_ZONE = 'Africa/Cairo'

# Enable internationalization (i18n)
# Allows translating the application to multiple languages
USE_I18N = True

# Enable localization (l10n)
# Formats dates, numbers, etc. according to locale
USE_L10N = True

# Use timezone-aware datetimes
# All datetimes in database are stored in UTC
USE_TZ = True

# ==============================================================================
# STATIC FILES (CSS, JavaScript, Images)
# ==============================================================================

# URL to access static files
# Example: http://localhost:8000/static/css/main.css
STATIC_URL = '/static/'

# Directories where Django looks for static files
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Global static files
]

# Directory where collectstatic command collects all static files
# Used in production to serve static files efficiently
STATIC_ROOT = BASE_DIR / 'staticfiles'


# MEDIA FILES (User Uploads)


# URL to access media files
# Example: http://localhost:8000/media/avatars/user1.jpg
MEDIA_URL = '/media/'

# Directory where uploaded files are stored
MEDIA_ROOT = BASE_DIR / 'media'

# CRISPY FORMS (Form Styling)
# Template pack for Crispy Forms
# We use Bootstrap 5 for styling
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'


# DJANGO REST FRAMEWORK (API)


REST_FRAMEWORK = {
    # Default authentication classes
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],

    # Default permission classes
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],

    # Pagination
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,

    # Date/time format
    'DATETIME_FORMAT': '%Y-%m-%d %H:%M:%S',
}


# CORS HEADERS (Cross-Origin Resource Sharing)

# Allow CORS from these origins
# In development: allow all
# In production: specify exact domains
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOWED_ORIGINS = [
        'https://yourdomain.com',
        'https://www.yourdomain.com',
    ]


# CHANNELS (WebSocket)

# Channel layers configuration
# Uses Redis for message passing between servers
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('REDIS_URL', default='redis://redis:6379/1')],
        },
    },
}


# CELERY (Background Tasks)

# Celery broker URL (where tasks are queued)
CELERY_BROKER_URL = config('REDIS_URL', default='redis://redis:6379/0')

# Celery result backend (where results are stored)
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://redis:6379/0')

# Celery task serialization format
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Celery timezone
CELERY_TIMEZONE = TIME_ZONE

# Celery task time limit (5 minutes)
CELERY_TASK_TIME_LIMIT = 5 * 60

# Celery task soft time limit (4 minutes - gives 1 min for cleanup)
CELERY_TASK_SOFT_TIME_LIMIT = 4 * 60


# EMAIL CONFIGURATION

# Email backend
# console: Prints emails to console (for development)
# smtp: Sends real emails via SMTP server (for production)
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend'
)

# SMTP settings (for production)
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='Catchy Bot <noreply@catchybot.com>')


# LOGGING

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    # Log formatters
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },

    # Log handlers (where to send logs)
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },

    # Loggers
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': config('LOG_LEVEL', default='INFO'),
            'propagate': True,
        },
        'apps': {  # Our custom apps
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


# CUSTOM SETTINGS

# Pagination size
PAGINATION_SIZE = 25

# Session settings
SESSION_COOKIE_AGE = 86400  # 24 hours in seconds
SESSION_SAVE_EVERY_REQUEST = False  # Only save if modified

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5 MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

# Lead Management Settings
LEAD_IMPORT_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB for lead import files
LEAD_REMINDER_OPTIONS = [
    ('15min', '15 minutes before'),
    ('30min', '30 minutes before'),
    ('1hour', '1 hour before'),
    ('2hours', '2 hours before'),
    ('1day', '1 day before'),
    ('2days', '2 days before'),
]


# SECURITY SETTINGS (Production)

if not DEBUG:
    # HTTPS/SSL settings
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Security headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'

    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# DEFAULT AUTO FIELD

# Default primary key field type
# BigAutoField: 64-bit integer (supports more records than AutoField)
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'