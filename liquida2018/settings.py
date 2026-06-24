import os
import ssl
from django.urls import reverse_lazy
from decouple import config
from django.contrib.messages import constants as messages
from celery.schedules import crontab
import django_heroku
import dj_database_url

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = config("SECRET_KEY", default="django-insecure-local-dev-key")
DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = [
    "127.0.0.1",
    # "192.168.0.4",
    "localhost",
    "liquidateresina.com.br",
    ".liquidateresina.com.br",
    "www.liquidateresina.com.br",
    "nataldeluzepremios2025.com.br",
    ".nataldeluzepremios2025.com.br",
    "www.nataldeluzepremios2025.com.br",
    "npt2025-688fdc500571.herokuapp.com", 
    ".npt2025-688fdc500571.herokuapp.com"
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "bcp",
    "cupom",
    "participante",
    'organizacao',
    'sorteio',
    'suporte',
    "lojista",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "widget_tweaks",
    "django_filters",
    "sorl.thumbnail",
    "storages",
    "import_export",
    "logentry_admin",
    "parsley",
    "anymail",
    "rest_framework",
    "django_session_timeout",
    "django_celery_results",
    "django_celery_beat",
]

MIDDLEWARE = [
    # Django Security & Core
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    
    # Third Party
    "django_session_timeout.middleware.SessionTimeoutMiddleware",
    
    # Custom Debug & Monitoring (apenas em DEBUG)
    "participante.middleware.debug.DebugMiddleware",
    
    # Custom Business Logic
    "participante.middleware.cards.CardsMiddleware",
    "participante.middleware.jornada.UpdateJornadaMiddleware",
    "participante.middleware.jornada.FinalizaJornadaMiddleware",
    "participante.middleware.auth.RoleBasedRedirectionMiddleware",
    "participante.middleware.auth.JornadaControlMiddleware",
    "participante.middleware.auth.ForcePasswordChangeMiddleware"
]

ROOT_URLCONF = "liquida2018.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(BASE_DIR, 'participante', 'templates'),
            os.path.join(BASE_DIR, 'lojista', 'templates'),
            os.path.join(BASE_DIR, 'cupom', 'templates'),
            os.path.join(BASE_DIR, 'bcp', 'templates'),
            os.path.join(BASE_DIR, 'suporte', 'templates'),
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.media",
                "participante.context_processors.postos_disponiveis",
                "participante.context_processors.documentos_revertidos",
            ],
        },
    },
]

WSGI_APPLICATION = "liquida2018.wsgi.application"

# Database Configuration
DATABASE_URL = config("DATABASE_URL", default="sqlite:///" + os.path.join(BASE_DIR, "db.sqlite3"))

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL)
}

if DEBUG:
    INSTALLED_APPS.append('silk')

if DEBUG:
    SILKY_STORAGE = "django.core.files.storage.FileSystemStorage"
    SILKY_PYTHON_PROFILER = True
    SILKY_PYTHON_PROFILER_MEMORY = True




# Otimizações para SQLite
if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    DATABASES['default']['OPTIONS'] = {
        'timeout': 30,  # 30 segundos de timeout
        'check_same_thread': False,
    }
    # Configurações de conexão otimizadas
    DATABASES['default']['CONN_MAX_AGE'] = 0  # Fechar conexões após cada request
    DATABASES['default']['ATOMIC_REQUESTS'] = False  # Desabilitar transações automáticas

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Fortaleza"
CELERY_TIMEZONE = "America/Fortaleza"
USE_I18N = True
USE_L10N = True
USE_TZ = True

DATE_INPUT_FORMATS = ["%d-%m-%Y"]
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10240

# Session settings
SESSION_EXPIRE_SECONDS = 1800  # 30 minutos
SESSION_EXPIRE_AFTER_LAST_ACTIVITY = True
SESSION_TIMEOUT_REDIRECT = "/"
SESSION_COOKIE_AGE = 1800  # 30 minutos
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True

# CSRF Configuration - Configuração simples e robusta
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000', 
    'http://127.0.0.1:8000',
    'https://liquidateresina.com.br',
    'https://www.liquidateresina.com.br',
    'http://liquidateresina.com.br',
    'http://www.liquidateresina.com.br',
    'https://nataldeluzepremios2025.com.br',
    'https://www.nataldeluzepremios2025.com.br',
    'https://npt2025-688fdc500571.herokuapp.com'
]
CSRF_USE_SESSIONS = False
CSRF_COOKIE_SAMESITE = 'Lax'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
    os.path.join(BASE_DIR, "bcp"),  # Add bcp directory
]
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "/static/"

# MEDIA_URL = '/media/'
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Static files storage
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# Configuração para desenvolvimento vs produção
USE_S3 = config("USE_S3", default=False, cast=bool)

# Definir sempre AWS_STORAGE_BUCKET_NAME para evitar erros de importação
# mesmo quando USE_S3=False (não interfere, pois StaticStorage não é usado)
AWS_STORAGE_BUCKET_NAME = config("AWS_STORAGE_BUCKET_NAME", default="lqd-2025")

if USE_S3:
    
    # Configuração S3 para produção
    AWS_ACCESS_KEY_ID = config("AWS_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = config("AWS_SECRET_ACCESS_KEY", default="")
    AWS_S3_REGION_NAME = config("AWS_S3_REGION_NAME", default="sa-east-1")
    AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com"

    MEDIA_LOCATION = "media"     # Pasta para uploads no S3
    
    # S3 Object Parameters
    AWS_S3_OBJECT_PARAMETERS = {
        "CacheControl": "max-age=86400",
    }
    
    # CORS Configuration
    AWS_S3_CORS_CONFIGURATION = {
        "CORSRules": [
            {
                "AllowedHeaders": ["*"],
                "AllowedMethods": ["GET", "HEAD", "PUT", "POST", "DELETE"],
                "AllowedOrigins": ["*"],
                "ExposeHeaders": ["ETag"]
            }
        ]
    }
    

    AWS_DEFAULT_ACL = None  # Bucket não permite ACLs, acesso público via política do bucket
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = False
    AWS_S3_VERIFY = True
    AWS_S3_ADDRESSING_STYLE = "virtual"
    AWS_S3_SIGNATURE_VERSION = 's3v4'  # Importante para sa-east-1

    # URLs e Storage para produção
   
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{MEDIA_LOCATION}/"   
    DEFAULT_FILE_STORAGE = "liquida2018.storage_backends.MediaStorage"
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media_temp')
    
    # Remover WhiteNoise quando usando S3
    STATIC_URL = "/static/"
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media') 
    STATIC_URL = "/static/"
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
    DEFAULT_FILE_STORAGE = "django.core.files.storage.FileSystemStorage"

EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
EMAIL_HOST = "smtp.mailgun.org"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("MAILGUN_SENDER_DOMAIN", default="example.com")
EMAIL_HOST_PASSWORD = config("MAILGUN_API_KEY", default="your-mailgun-api-key")
DEFAULT_FROM_EMAIL = "suporte@liquidateresina.com.br"
SERVER_EMAIL = DEFAULT_FROM_EMAIL

ANYMAIL = {
    "MAILGUN_API_KEY": config("MAILGUN_API_KEY", default="your-mailgun-api-key"),
    "MAILGUN_SENDER_DOMAIN": config("MAILGUN_SENDER_DOMAIN", default="example.com"),
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "participante.authentication.CPFAuthBackend",
)

# Login settings
LOGIN_URL = "/"
LOGIN_REDIRECT_URL = "participante:dashboard"

SOCIAL_AUTH_FACEBOOK_KEY = "340442496482403"
SOCIAL_AUTH_FACEBOOK_SECRET = "8c550fd5dd91ec4ebce457a00afea8ea"

LOGOUT_REDIRECT_URL = "/"
DEBUG_PROPAGATE_EXCEPTIONS = True


django_heroku.settings(locals(), staticfiles=False)

# Celery Configuration
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

redis_url = config("REDIS_URL", default="redis://localhost:6379/0")

# Fix SSL configuration for rediss:// URLs
if redis_url.startswith("rediss://"):
    # Parse the URL
    parsed = urlparse(redis_url)
    query_params = parse_qs(parsed.query)
    
    # Add or update ssl_cert_reqs parameter
    query_params['ssl_cert_reqs'] = ['CERT_NONE']
    
    # Rebuild the URL
    new_query = urlencode(query_params, doseq=True)
    redis_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

CELERY_BROKER_URL = redis_url
CELERY_RESULT_BACKEND = redis_url

# Celery Configuration
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "America/Sao_Paulo"
CELERY_ENABLE_UTC = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_RETRY = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = 10
CELERY_BROKER_TRANSPORT = "redis"
CELERY_REDIS_MAX_CONNECTIONS = 20
CELERY_WORKER_MAX_TASKS_PER_CHILD = 10
CELERY_WORKER_CONCURRENCY = 4
CELERY_TASK_SOFT_TIME_LIMIT = 3600  # 1 hour
CELERY_TASK_TIME_LIMIT = 3660  # 1 hour and 1 minute

# SSL configuration for rediss:// URLs
if redis_url.startswith("rediss://"):
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        "visibility_timeout": 43200,  # 12 hours
        "fanout_prefix": True,
        "fanout_patterns": True,
        "ssl_cert_reqs": ssl.CERT_NONE,
    }
else:
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        "visibility_timeout": 43200,  # 12 hours
        "fanout_prefix": True,
        "fanout_patterns": True,
    }

USE_CELERY_FOR_PDF = True

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Silk Configuration
SILKY_STORAGE = "django.core.files.storage.FileSystemStorage"
SILKY_PYTHON_PROFILER = True
SILKY_PYTHON_PROFILER_MEMORY = True

# Import local settings if they exist
# try:
#     from .local_settings import *
# except ImportError:
#     pass
