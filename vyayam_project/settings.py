"""
VYAYAM STRENGTH TRAINING - DJANGO SETTINGS
Django settings for vyayam_project
"""

import os
from pathlib import Path
import dj_database_url  # ADDED

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.environ['DJANGO_SECRET_KEY']  # Fail-fast: must be set in environment; no insecure fallback allowed

DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = [h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',') if h.strip()]
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1']
if not DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = ['.onrender.com']  # ADDED

CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in
    os.environ.get('DJANGO_CSRF_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000').split(',')
]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'strength_app',
    'therapist_app',
]

LOGIN_URL = '/therapist/login/'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'strength_app.middleware.PermissionsPolicyMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'vyayam_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'strength_app' / 'templates'],
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

WSGI_APPLICATION = 'vyayam_project.wsgi.application'


# Database — CHANGED to dj_database_url
_db_url = os.environ.get('DATABASE_URL', '')
if _db_url:
    DATABASES = {
        'default': dj_database_url.config(
            default=_db_url,
            conn_max_age=600,
            ssl_require=not DEBUG,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True


STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'strength_app' / 'static',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Pain (0-10) at/above which an exercise auto-skips when its PrescriptionItem has no
# therapist-set pain_stop_threshold (and for any flow without a therapist value).
PAIN_STOP_THRESHOLD_DEFAULT = 5
# Pain at/above which the WHOLE session pauses, regardless of per-exercise threshold.
PAIN_SESSION_PAUSE_THRESHOLD = 8

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'vyayam-rate-limit',
    }
}

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
# R2-W5: the previous config set BOTH a 7-day age AND expire-at-browser-
# close — contradictory. Decision: 7-day persistent sessions. This is a
# personal-phone PWA where mid-programme users return daily; forcing a
# phone+password login on every browser restart kills adherence, and
# browser-close rarely fires on mobile anyway. Therapist/coach consoles
# share the setting; their value is staff-managed Django auth.
SESSION_COOKIE_AGE = 86400 * 7
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SAMESITE = 'Lax'

X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

if not DEBUG:
    # Render terminates TLS at its proxy; without this gunicorn sees HTTP and
    # HSTS / SSL-redirect / Secure cookies never engage.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SSL_REDIRECT', 'False').lower() in ('true', '1')
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging — CHANGED: removed file handler (Render disk is ephemeral)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
# ── R2-U1: email (password-reset links) ──────────────────────────────────
# Dev default prints emails to the console; production sets SMTP via env.
EMAIL_BACKEND = os.environ.get(
    'DJANGO_EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend' if DEBUG
    else 'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.environ.get('DJANGO_EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('DJANGO_EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('DJANGO_EMAIL_USE_TLS', 'True').lower() in ('true', '1', 'yes')
DEFAULT_FROM_EMAIL = os.environ.get('DJANGO_DEFAULT_FROM_EMAIL', 'VYAYAM <noreply@vyayam.app>')
