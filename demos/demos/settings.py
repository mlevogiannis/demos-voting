# -*- encoding: utf-8 -*-
# File: settings.py

"""
Django settings for demos project.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Quick-start development settings - unsuitable for production
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
    DEVEL_DIR = os.path.join(os.path.dirname(BASE_DIR), 'devel')


# UNIX-domain sockets are placed under RUN_DIR, app data under VARLIB_DIR

RUN_DIR = '/run/demos-voting'
VARLIB_DIR = '/var/lib/demos-voting'

if DEVELOPMENT:
    
    RUN_DIR = os.path.join(DEVEL_DIR, 'sockets')
    VARLIB_DIR = os.path.join(DEVEL_DIR, 'data')


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

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'common/templates')
        ],
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
                'demos.common.utils.context_processors.common',
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

WSGI_APPLICATION = 'demos.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'demos_voting',
        'USER': 'demos_voting',
        #'PASSWORD': '',
        #'HOST': '',
        #'PORT': '',
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
TIME_ZONE = 'UTC'

USE_I18N = True
USE_L10N = True

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'common/locale'),
]


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'common/static'),
]

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


# Logging
# https://docs.djangoproject.com/en/1.8/topics/logging/

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'syslog': {
            'level': 'INFO',
            'class': 'logging.handlers.SysLogHandler',
            'address': '/dev/log', # Linux-specific
        }
    },
    'loggers': {
        'root': {
            'handlers': ['syslog',]
            },
        'django': {
            'handlers': ['mail_admins', 'syslog'],
            'level': 'INFO',
        },
        'demos': {
            'handlers': ['mail_admins', 'syslog'],
            'level': 'INFO',
        }
    },
}

if DEVELOPMENT:
    
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
            },
        },
        'loggers': {
            'root': {
                'handlers': ['console']
            },
            'django': {
                'handlers': ['console'],
                'level': 'DEBUG',
            },
            'django.request': {
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
    }


# Security Middleware
# https://docs.djangoproject.com/en/1.8/ref/middleware/#module-django.middleware.security

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_SECONDS = 31536000

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

if DEVELOPMENT:
    
    SECURE_BROWSER_XSS_FILTER = False
    SECURE_CONTENT_TYPE_NOSNIFF = False
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_SECONDS = 0
    
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False


# Demos-specific configuration

DEMOS_APPS = []    # one or more of: ea, bds, abb, vbb

DEMOS_CONFIG = {
    
    'ea': {
        
        # Election configuration
        
        'MAX_BALLOTS': 100000,
        'MAX_OPTIONS': 128,
        'MAX_TRUSTEES': 128,
        'MAX_QUESTIONS': 32,
        
        # demos-crypto connection parameters, see:
        # https://docs.python.org/3/library/socket.html
        
        # CRYPTO_AF: e.g. 'AF_UNIX' or 'AF_INET' or 'AF_INET6'
        # CRYPTO_ADDR: e.g. '/run/demos-crypto.sock' or ('127.0.0.1', 8999)
        
        'CRYPTO_AF': 'AF_UNIX',
        'CRYPTO_ADDR': os.path.join(RUN_DIR, 'demos-crypto.sock'),
        
        # Performance settings, they affect CPU and RAM usage, etc
        
        'BATCH_SIZE': 128,
        
        'RECV_MAX': 67108864,   # 64 MB
        'RECV_TIMEOUT': 900,   # 15 mins
        
        # Certificate Authority (X.509 / RSA)
        
        # CA_CERT_PEM: e.g. '/etc/pki/CA/cacert.pem',
        # CA_PKEY_PEM: e.g. '/etc/pki/CA/private/cakey.pem',
        
        # If DEVELOPMENT is True and pem-file paths are empty or invalid,
        # self-signed certificates will be generated
        
        'CA_CERT_PEM': '',
        'CA_PKEY_PEM': '',
        'CA_PKEY_PASSPHRASE': '',
    },
    
    'bds': {
        
        # Performance settings, they affect CPU and RAM usage, etc
        
        'BATCH_SIZE': 128,
        
        # Absolute path to the directory that will hold machine-local files
        
        'FILESYSTEM_ROOT': os.path.join(VARLIB_DIR, 'bds'),
    },
    
    'abb': {
        
        # Performance settings, they affect CPU and RAM usage, etc
        
        'BATCH_SIZE': 128,
        
        # Absolute path to the directory that will hold machine-local files
        
        'FILESYSTEM_ROOT': os.path.join(VARLIB_DIR, 'abb'),
    },
    
    'vbb': {
    },
}

DEMOS_URL = {
    'ea': 'https://demos-ea.domain-name.example/',
    'bds': 'https://demos-bds.domain-name.example/',
    'abb': 'https://demos-abb.domain-name.example/',
    'vbb': 'https://demos-vbb.domain-name.example/',
}

DEMOS_API_URL = {
    'ea': 'https://api.demos-ea.domain-name.example/',
    'bds': 'https://api.demos-bds.domain-name.example/',
    'abb': 'https://api.demos-abb.domain-name.example/',
    'vbb': 'https://api.demos-vbb.domain-name.example/',
}

# In case the API URLs are SSL-enabled and use self-signed certificates,
# their verification can be disabled to allow requests among servers
# http://docs.python-requests.org/en/latest/user/advanced/#ssl-cert-verification

# DEMOS_API_VERIFY = False    # the default is True


INSTALLED_APPS += [ 'demos.apps.%s' % app for app in DEMOS_APPS ]
LOCALE_PATHS += [ os.path.join(BASE_DIR, 'apps/%s/locale' % app) for app in DEMOS_APPS ]


# Celery-specific configuration
# http://docs.celeryproject.org/en/latest/getting-started/brokers/index.html

BROKER_URL = 'redis+socket://' + os.path.join(RUN_DIR, 'redis.sock')
CELERY_RESULT_BACKEND = 'redis'

CELERY_TASK_SERIALIZER = 'custom-json'
CELERY_RESULT_SERIALIZER = 'custom-json'
CELERY_ACCEPT_CONTENT = ['custom-json', 'json', 'msgpack']

if DEVELOPMENT and False:
    
    # Alternative config, only using Django + existing db
    # Note: introduces dependency on python-SQLAlchemy
    
    BROKER_URL = 'django://'
    INSTALLED_APPS += [ 'kombu.transport.django' ]
    CELERY_RESULT_BACKEND = 'db+postgresql://%(USER)s:%(PASSWORD)s@' \
        '%(HOST)s:%(PORT)s/%(NAME)s' % DATABASES['default']

