# BASE IMAGE

# Use Python 3.11 slim version as base image
# Why slim? Smaller size (150MB vs 900MB), faster builds, better for production
# Contains only essential Python tools, no unnecessary packages
FROM python:3.11-slim


# ENVIRONMENT VARIABLES

# Prevents Python from writing .pyc files to disc
# Why? .pyc files are bytecode cache, not needed in containers
# Keeps the container clean and saves space
ENV PYTHONDONTWRITEBYTECODE=1

# Prevents Python from buffering stdout and stderr
# Why? We want to see logs immediately, not buffered
# Important for debugging and monitoring
ENV PYTHONUNBUFFERED=1


# WORKING DIRECTORY

# Set working directory inside container to /code
# All subsequent commands will run from this directory
# This is where our Django project will live
WORKDIR /code


# SYSTEM DEPENDENCIES

# Update package list and install system dependencies
# Breaking down the command:
# 1. apt-get update: Updates the package list
# 2. apt-get install -y: Installs packages without confirmation
# 3. postgresql-client: Required to connect to PostgreSQL database
# 4. gettext: Required for Django translations (internationalization)
# 5. && rm -rf /var/lib/apt/lists/*: Cleans up to reduce image size

RUN apt-get update && apt-get install -y \
    postgresql-client \
    gettext \
    && rm -rf /var/lib/apt/lists/*


# PYTHON DEPENDENCIES

# Copy requirements file first (before copying entire project)
# Why first? Docker layer caching!
# If requirements.txt doesn't change, Docker will use cached layer
# This speeds up builds significantly
COPY requirements.txt /code/

# Upgrade pip to latest version
# Ensures we have latest bug fixes and features
RUN pip install --upgrade pip

# Install Python dependencies from requirements.txt
# --no-cache-dir: Don't cache packages (saves space)
# This is the slowest step, but cached if requirements.txt unchanged
RUN pip install --no-cache-dir -r requirements.txt


# PROJECT FILES

# Copy entire project to working directory
# This happens last to utilize Docker's layer caching
# If we change code but not requirements, only this layer rebuilds
COPY . /code/


# EXPOSE PORT

# Expose port 8000 for the Django application
# This is the default Django development server port
# Note: This is documentation only, doesn't actually open the port
# Port mapping is done in docker-compose.yml
EXPOSE 8000


# DEFAULT COMMAND

# Default command when container starts
# This will be overridden by docker-compose.yml
# Format: ["executable", "param1", "param2"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


# NOTES
# ==============================================================================
# 1. Build image: docker build -t catchybot:latest .
# 2. Run container: docker run -p 8000:8000 catchybot:latest
# 3. But we'll use docker-compose instead (easier!)
# ==============================================================================