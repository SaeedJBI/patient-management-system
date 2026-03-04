"""
Production settings for the PMS project.
"""
from .base import *
from decouple import config
import dj_database_url
import django
from django.template import context

# SECURITY WARNING: keep the secret key used in production secret!
DEBUG = True

# Production hosts - set these in Render dashboard
ALLOWED_HOSTS = config('ALLOWED_HOSTS', cast=lambda v: [s.strip() for s in v.split(',')])

# Database - Use DATABASE_URL from Render
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL'),
        conn_max_age=600,
        ssl_require=True
    )
}

# Security settings for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Temporary workaround for template context issue
original_copy = context.Context.__copy__

def patched_copy(self):
    # Create a new context with the same dicts
    new_context = context.Context(self.dicts)
    return new_context

context.Context.__copy__ = patched_copy

# Update MIDDLEWARE to include WhiteNoise (add after SecurityMiddleware)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this line
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'core.middleware.UserLanguageMiddleware',
    # 'core.middleware.StaffAdminRedirectMiddleware',  # Temporarily disabled
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Static files configuration with WhiteNoise
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Optional: Add WhiteNoise configuration for better performance
WHITENOISE_USE_FINDERS = True
WHITENOISE_MANIFEST_STRICT = False  # This helps with missing files like source maps
WHITENOISE_ALLOW_ALL_ORIGINS = True