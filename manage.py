
# CATCHY BOT CRM - DJANGO MANAGEMENT SCRIPT
# This is Django's command-line utility for administrative tasks
#
# Common commands:
# - python manage.py runserver          # Start development server
# - python manage.py makemigrations     # Create database migrations
# - python manage.py migrate            # Apply migrations to database
# - python manage.py createsuperuser    # Create admin user
# - python manage.py shell              # Open Django shell
# - python manage.py test               # Run tests
# - python manage.py collectstatic      # Collect static files for production
#
# In Docker:
# - docker compose exec web python manage.py [command]
# ==============================================================================

import os
import sys


def main():
    """
    Run administrative tasks

    This function:
    1. Sets the Django settings module
    2. Imports Django's management utility
    3. Executes the command-line arguments
    """

    # Set the default Django settings module
    # Points to config/settings.py
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

    try:
        # Import Django's command-line utility
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # If Django is not installed, show helpful error message
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Execute the command with arguments from command line
    # sys.argv contains: ['manage.py', 'command', 'arg1', 'arg2', ...]
    execute_from_command_line(sys.argv)


# Entry point
# This runs when you execute: python manage.py [command]
if __name__ == '__main__':
    main()