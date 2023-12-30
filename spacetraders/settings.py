import dj_database_url
import os
from pathlib import Path
import sys


# Project paths
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = str(Path(__file__).resolve().parents[1])
PROJECT_DIR = str(Path(__file__).resolve().parents[0])
# Add PROJECT_DIR to the system path.
#sys.path.insert(0, PROJECT_DIR)


# Application definition
DEBUG = os.environ.get("DEBUG", False) == "True"
SECRET_KEY = os.environ.get("SECRET_KEY", "PlaceholderSecretKey")
if not DEBUG:
    ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost").split(",")
else:
    ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "spacetraders.urls"
WSGI_APPLICATION = "spacetraders.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
API_URL = API_URL_V2 = "https://api.spacetraders.io/v2"
API_TOKEN = os.environ.get("API_TOKEN", "PlaceholderToken")
STATIC_CONTEXT_VARS = {}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_extensions",
    "django_rq",
    "galaxy",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(PROJECT_DIR, "templates"),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": DEBUG,
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "spacetraders.context_processors.template_context",
            ],
        },
    },
]


# Database configuration
DATABASES = {
    # Defined in the DATABASE_URL env variable.
    "default": dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
    ),
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 16,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]


# Internationalization
LANGUAGE_CODE = os.environ.get("LANGUAGE_CODE", "en-us")
TIME_ZONE = os.environ.get("TZ", "UTC")
USE_TZ = True
USE_I18N = True
USE_L10N = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = (os.path.join(BASE_DIR, "spacetraders", "static"),)


# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s %(levelname)-12s %(name)-12s %(message)s",
        },
        "rq_console": {
            "format": "%(asctime)s %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "stream": sys.stdout,
            "level": "WARNING",
        },
        "spacetraders": {
            "class": "logging.FileHandler",
            "formatter": "verbose",
            "filename": "spacetraders.log",
            "level": "INFO",
        },
        "rq_console": {
            "class": "rq.logutils.ColorizingStreamHandler",
            "formatter": "rq_console",
            "exclude": ["%(asctime)s"],
            "level": "INFO",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
        },
        "spacetraders": {
            "handlers": ["spacetraders"],
            "level": "INFO",
        },
        "rq.worker": {
            "handlers": ["rq_console"],
            "level": "INFO"
        },
    }
}


# django-rq
RQ_QUEUES = {
    "default": {
        "HOST": "localhost",
        "PORT": 6379,
        "DB": 0,
        "DEFAULT_TIMEOUT": 360,
        "DEFAULT_RESULT_TTL": 60,
    },
}
