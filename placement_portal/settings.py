"""
Django settings for placement_portal project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------------------------------------------------
# SECURITY
# -------------------------------------------------------------------

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-pl@cement-p0rtal-dev-key-ch@nge-in-production!'
)

DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get(
    'ALLOWED_HOSTS',
    '127.0.0.1'
).split(',')

CSRF_TRUSTED_ORIGINS = [
    "https://placementstatsdau.up.railway.app",
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

CSRF_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SAMESITE = "Lax"

# -------------------------------------------------------------------
# APPLICATIONS
# -------------------------------------------------------------------

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'portal',
]

# -------------------------------------------------------------------
# MIDDLEWARE
# -------------------------------------------------------------------

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# -------------------------------------------------------------------
# URLS / TEMPLATES
# -------------------------------------------------------------------

ROOT_URLCONF = 'placement_portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'placement_portal.wsgi.application'

# -------------------------------------------------------------------
# DATABASE
# -------------------------------------------------------------------

DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600
    )
}

# -------------------------------------------------------------------
# SESSION CONFIG
# -------------------------------------------------------------------

SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# -------------------------------------------------------------------
# PASSWORD VALIDATION
# -------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'
    },
]

# -------------------------------------------------------------------
# INTERNATIONALIZATION
# -------------------------------------------------------------------

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True
USE_TZ = True

# -------------------------------------------------------------------
# STATIC FILES
# -------------------------------------------------------------------

STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# -------------------------------------------------------------------
# MEDIA FILES
# -------------------------------------------------------------------

MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'

# -------------------------------------------------------------------
# DEFAULT PRIMARY KEY
# -------------------------------------------------------------------

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------------------------------------------------
# AUTH REDIRECTS
# -------------------------------------------------------------------

LOGIN_URL = '/auth/login/'

LOGIN_REDIRECT_URL = '/dashboard/'

# -------------------------------------------------------------------
# API KEYS
# -------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get(
    'ANTHROPIC_API_KEY',
    ''
)

# -------------------------------------------------------------------
# EMAIL CONFIGURATION
# -------------------------------------------------------------------

EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend'
)

EMAIL_HOST = os.environ.get(
    'EMAIL_HOST',
    'smtp.gmail.com'
)

EMAIL_PORT = int(
    os.environ.get('EMAIL_PORT', 587)
)

EMAIL_USE_TLS = os.environ.get(
    'EMAIL_USE_TLS',
    'True'
).lower() in ('true', '1', 'yes')

EMAIL_HOST_USER = os.environ.get(
    'EMAIL_HOST_USER',
    ''
)

EMAIL_HOST_PASSWORD = os.environ.get(
    'EMAIL_HOST_PASSWORD',
    ''
)

DEFAULT_FROM_EMAIL = os.environ.get(
    'DEFAULT_FROM_EMAIL',
    f'Placement Portal <{EMAIL_HOST_USER}>'
)