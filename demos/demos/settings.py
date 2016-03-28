# -*- encoding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

"""
Django settings for demos project.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

"""


# Quick-start settings
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

ALLOWED_HOSTS = [
    '',
]

ADMINS = [
    ('Root', 'root@localhost'),
]


# SECURITY WARNING: keep the secret key used in production secret!

SECRET_KEY = ''

# SECURITY WARNING: don't run with debug or development turned on in production!

DEBUG = False
DEVELOPMENT = False

if DEVELOPMENT:
    DEBUG = True


import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Runtime data (e.g. UNIX-domain sockets) are placed in RUN_DIR,
# application data (e.g. ballots, certificates) are placed in DATA_DIR.

RUN_DIR = '/run/demos-voting'
DATA_DIR = '/var/lib/demos-voting'

if DEVELOPMENT:
    RUN_DIR = os.path.join(os.path.dirname(BASE_DIR), 'run')
    DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), 'data')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
]

ROOT_URLCONF = 'demos.urls'

WSGI_APPLICATION = 'demos.wsgi.application'


# Templates
# https://docs.djangoproject.com/en/1.8/ref/settings/#templates

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
        },
    },
]

if DEVELOPMENT:
    TEMPLATES[0]['APP_DIRS'] = True
    del TEMPLATES[0]['OPTIONS']['loaders']


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'demos_voting',
        'USER': 'demos_voting',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

from django.utils.translation import ugettext_lazy as _

LANGUAGES = [
    ('el', _('Greek')),
    ('en', _('English')),
]

LANGUAGE_CODE = 'en-us'

USE_TZ = True
TIME_ZONE = 'Europe/Athens'

USE_I18N = True
USE_L10N = True

LOCALE_PATHS = []


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(os.path.dirname(BASE_DIR), 'static')


# Sending email
# https://docs.djangoproject.com/en/1.8/topics/email/

EMAIL_HOST = ''
EMAIL_PORT = 587
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = ''
SERVER_EMAIL = ''

if DEVELOPMENT:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# Security Middleware
# https://docs.djangoproject.com/en/1.8/ref/middleware/#module-django.middleware.security

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000

if DEVELOPMENT:
    SECURE_BROWSER_XSS_FILTER = False
    SECURE_CONTENT_TYPE_NOSNIFF = False
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_SECONDS = 0


CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

if DEVELOPMENT:
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False


# Logging
# https://docs.djangoproject.com/en/1.8/topics/logging/

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
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
        },
    },
    'loggers': {
        'root': {
            'handlers': ['syslog']
            },
        'django': {
            'handlers': ['mail_admins', 'syslog'],
            'level': 'INFO',
        },
        'demos': {
            'handlers': ['mail_admins', 'syslog'],
            'level': 'INFO',
        },
    },
}

if DEVELOPMENT:
    
    LOGGING['handlers'] = {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    }
    
    LOGGING['loggers'] = {
        'root': {
            'handlers': ['console']
        },
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'demos': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }


# DEMOS Voting configuration

# DEMOS_APPS: One or more of 'ea', 'bds', 'abb', 'vbb'. Warning! The apps must
# be isolated (with regard to data storage and access to the server), in order
# to support voter privacy. Never use multiple apps on the same production
# server. This feature is intended only to be used for development purposes.

DEMOS_APPS = []

INSTALLED_APPS += ['demos.%s' % path for path in (['common'] + ['apps.%s' % app for app in DEMOS_APPS])]
LOCALE_PATHS += [os.path.join(BASE_DIR, '%s/locale' % p) for p in (['common'] + ['apps/%s' % a for a in DEMOS_APPS])]

# DEMOS_URLS: A dictionary of strings, each one representing the URL by which
# an app is served. Always use HTTPS URLs.

DEMOS_URLS = {
    'ea' : 'https://www.example.org/demos/ea/',
    'bds': 'https://www.example.org/demos/bds/',
    'abb': 'https://www.example.org/demos/abb/',
    'vbb': 'https://www.example.org/demos/vbb/',
}

# DEMOS_API_URLS: Same as DEMOS_URLS, but for the internal API. It is
# recommended that these URLs are accessible only through a private network.

DEMOS_API_URLS = {
    'ea' : 'https://api.example.local/demos/ea/',
    'bds': 'https://api.example.local/demos/bds/',
    'abb': 'https://api.example.local/demos/abb/',
    'vbb': 'https://api.example.local/demos/vbb/',
}

# DEMOS_API_VERIFY_SSL: If False, the SSL certificates for API requests will
# not be verified. Required if the servers use self-signed SSL certificates.
# http://docs.python-requests.org/en/latest/user/advanced/#ssl-cert-verification

DEMOS_API_VERIFY_SSL = True

# DEMOS_BATCH_SIZE: Controls how many objects (e.g. ballots) are processed in
# a single iteration.

DEMOS_BATCH_SIZE = 128

# DEMOS_DATA_DIR: Absolute path to the directory that will hold local files.

DEMOS_DATA_DIR = DATA_DIR

# DEMOS_CRYPTO_*: (ea only) Connection parameters for demos-crypto. See:
# https://docs.python.org/3/library/socket.html

DEMOS_CRYPTO_AF = 'AF_UNIX'
DEMOS_CRYPTO_ADDR = os.path.join(RUN_DIR, 'demos-crypto.sock')

# DEMOS_CA_*: (ea only) Certificate authority configuration. If both
# CA_CERT_FILE and CA_PKEY_FILE are empty, self-signed certificates will
# be generated. CA_PKEY_PASSPHRASE is optional.

DEMOS_CA_CERT_FILE = ''
DEMOS_CA_PKEY_FILE = ''
DEMOS_CA_PKEY_PASSPHRASE = ''

# DEMOS_MAX_*: The maximum number of ballots, questions per referendum,
# options per question, parties per election and candidates per party.

DEMOS_MAX_BALLOTS = 10000
DEMOS_MAX_ELECTION_PARTIES = 50
DEMOS_MAX_ELECTION_CANDIDATES = 50
DEMOS_MAX_REFERENDUM_QUESTIONS = 50
DEMOS_MAX_REFERENDUM_OPTIONS = 50


# Celery configuration
# http://docs.celeryproject.org/en/latest/getting-started/brokers/index.html

INSTALLED_APPS += ['kombu.transport.django']

BROKER_URL = 'django://'
CELERY_RESULT_BACKEND = 'db+postgresql://%(USER)s:%(PASSWORD)s@%(HOST)s:%(PORT)s/%(NAME)s' % DATABASES['default']

CELERY_TASK_SERIALIZER = 'custom-json'
CELERY_RESULT_SERIALIZER = 'custom-json'
CELERY_ACCEPT_CONTENT = ['custom-json', 'json', 'msgpack']

