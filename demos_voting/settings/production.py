from __future__ import absolute_import, division, print_function, unicode_literals

from six.moves.urllib.parse import urljoin

from demos_voting.settings.base import *

# Quick-start settings
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

DATA_DIR = ''

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ''

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    'www.example.com',
]

ADMINS = [
    ('Administrator', 'admin@example.com'),
]

# Application definition

INSTALLED_APPS[:0] = [
    # 'demos_voting.ballot_distributor',
    # 'demos_voting.bulletin_board',
    # 'demos_voting.election_authority',
    # 'demos_voting.vote_collector',
]

# TEMPLATES[0]['DIRS'] = []

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'demos_voting',
        'USER': 'demos_voting',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    },
}

# Running behind a reverse proxy

FORCE_SCRIPT_NAME = None
USE_X_FORWARDED_HOST = False

# Cookie configuration

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

if FORCE_SCRIPT_NAME:
    CSRF_COOKIE_PATH = FORCE_SCRIPT_NAME
    LANGUAGE_COOKIE_PATH = FORCE_SCRIPT_NAME
    SESSION_COOKIE_PATH = FORCE_SCRIPT_NAME

# Security middleware
# https://docs.djangoproject.com/en/1.11/ref/middleware/#module-django.middleware.security

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_SSL_HOST = None
# SECURE_SSL_REDIRECT = True
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

# LOCALE_PATHS = []

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_ROOT = os.path.join(DATA_DIR, 'static/')
STATIC_URL = urljoin(FORCE_SCRIPT_NAME or '/', 'static/')
# STATICFILES_DIRS = []

# Managing files
# https://docs.djangoproject.com/en/1.11/topics/files/

# SECURITY WARNING: Do NOT configure the web server to serve the files in
# 'MEDIA_ROOT', they will be served by the application instead.

MEDIA_ROOT = os.path.join(DATA_DIR, 'media/')

FILE_UPLOAD_PERMISSIONS = 0o600
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o700

# Sending email
# https://docs.djangoproject.com/en/1.11/topics/email/

EMAIL_HOST = ''
EMAIL_PORT = 587
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = 'webmaster@example.com'
SERVER_EMAIL = 'root@example.com'

# Logging
# https://docs.djangoproject.com/en/1.11/topics/logging/

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'syslog': {
            'level': 'INFO',
            'class': 'logging.handlers.SysLogHandler',
            'address': '/dev/log',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
            'filters': ['require_debug_false'],
        },
    },
    'loggers': {
        'root': {
            'handlers': ['syslog']
        },
        'django': {
            'level': 'INFO',
            'handlers': ['mail_admins', 'syslog'],
        },
        'demos_voting': {
            'level': 'INFO',
            'handlers': ['mail_admins', 'syslog'],
        },
    },
}

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# django-allauth
# https://github.com/pennersr/django-allauth

ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https'

ACCOUNT_IS_OPEN_FOR_SIGNUP = False  # custom setting
SOCIALACCOUNT_IS_OPEN_FOR_SIGNUP = False  # custom setting

# Celery
# http://docs.celeryproject.org/en/latest/django/index.html

CELERY_BROKER_URL = 'redis://'

# DEMOS Voting
# See 'settings/base.py' for more information.

DEMOS_VOTING_URLS = {
    'ballot_distributor': 'https://www.example.com/demos-voting/ballot-distributor/',
    'bulletin_board': 'https://www.example.com/demos-voting/bulletin-board/',
    'election_authority': 'https://www.example.com/demos-voting/election-authority/',
    'vote_collector': 'https://www.example.com/demos-voting/vote-collector/',
}
