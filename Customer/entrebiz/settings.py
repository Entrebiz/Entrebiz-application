"""
Django settings for entrebiz project.

Generated by 'django-admin startproject' using Django 3.2.10.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
import os
from pathlib import Path

import environ
# Initialise environment variables
env = environ.Env()
environ.Env.read_env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = eval(env('DEBUG'))

ALLOWED_HOSTS = eval(env('ALLOWED_HOSTS'))

CORS_ORIGIN_ALLOW_ALL=eval(env('CORS_ORIGIN_ALLOW_ALL'))

CORS_ORIGIN_WHITELIST = eval(env('CORS_ORIGIN_WHITELIST'))

CSRF_TRUSTED_ORIGINS = eval(env('CSRF_TRUSTED_ORIGINS'))

# Application definition

INSTALLED_APPS = [
    'whitenoise.runserver_nostatic',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'utils',
    'Transactions',
    'EntrebizAdmin',
    'corsheaders',
    'django_user_agents',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.authentication_middleware.TwoFactorValidateMiddleware',
    'accounts.middleware.authentication_middleware.UserStatusMiddleware',
    'accounts.middleware.authentication_middleware.UserAccountLockedMiddleware',
    'django_user_agents.middleware.UserAgentMiddleware',
]

ROOT_URLCONF = 'entrebiz.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates/')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'entrebiz.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DATABASE_NAME'),
        'USER': env('DATABASE_USER'),
        'PASSWORD': env('DATABASE_PASS'),
        'HOST': env('DATABASE_HOST'),
    },
}


# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'
# TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/
STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]
# STATIC_ROOT = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR,'staticfiles')
MEDIA_URL = '/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login'

# DOMAIN = 'http://localhost:8000/setPassword/'
CURRENT_DOMAIN = env("DOMAIN")
DOMAIN = f'{env("DOMAIN")}/setPassword/'
ACTIVATION_LINK_EXP = 7  # IN DAYS
OTP_NUMBER_RANGE = [111111,999999]
DATE_FORMAT = "%Y-%m-%d"
OTP_EXP = 7
MASTER_ACC_NO = '10000001' #when it becomes dynamic, please give True to master account field in accounts table
DEFAULT_ADD = 1000000
MAX_FILE_SIZE = 10485760 #10 MB
ALLOWED_FORMATS = ['.jpeg','.jpg','.pdf','.tiff','.png']
CSRF_FAILURE_VIEW = "Transactions.accounttoaccount.views.access_forbidden"
EXCLUDED_TRANSACTION_TYPES = ["Conversion", "Currency Conversion", "Company Inward Remittance Commission", "Other Charges", "Inward Remittance", "Refund"]

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')

#TWILIO
TWILIO_ACCOUNT_SID = env('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = env('TWILIO_AUTH_TOKEN')
TWILIO_NUMBER = env('TWILIO_NUMBER')

FEE_CALCULATE_MINIMUM_DURATION = 15 # in days

#celery
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'

# AWS S3 storage
AWS_S3_ACCESS_KEY_ID = env('AWS_S3_ACCESS_KEY_ID')
AWS_S3_SECRET_ACCESS_KEY = env('AWS_S3_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_QUERYSTRING_AUTH = eval(env('AWS_QUERYSTRING_AUTH'))
AWS_DEFAULT_ACL = env('AWS_DEFAULT_ACL')
DEFAULT_FILE_STORAGE=env('DEFAULT_FILE_STORAGE')
AWS_S3_MEDIA_URL=env('AWS_S3_MEDIA_URL')
AWS_S3_BUCKET_URL=env('AWS_S3_BUCKET_URL')

LOGGING = {
    'version': 1,
    'loggers': {
        'lessons': {
            'handlers': ['file'],
            'level': 'INFO',
            # 'propagate': True,
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': './logs/debug.log',
            'when': 'D', # this specifies the interval
            'interval': 30, # defaults to 1, only necessary for other values
            'backupCount': 5, # how many backup file to keep, 30 days
            'formatter': 'app',
        },
    },
    "formatters": {
        "app": {
            "format": (
                u"%(asctime)s [%(levelname)-8s] "
                "(%(pathname)s/%(funcName)s.%(lineno)d) %(message)s"
            ),
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
}
