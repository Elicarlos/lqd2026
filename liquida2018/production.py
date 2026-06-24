"""
Production settings for Natal de Premios
"""
from .settings import *

# Security settings for production
DEBUG = False
ALLOWED_HOSTS = [
    "liquidateresina.com.br",
    ".liquidateresina.com.br",
    "www.liquidateresina.com.br",
    "lqd2025-f3665d0be439.herokuapp.com",
    ".lqd2025-f3665d0be439.herokuapp.com",
    "lqd2024-ff3963465f8b.herokuapp.com",
    ".lqd2024-ff3963465f8b.herokuapp.com",
    "lqd2025-23ddd0fe8fa9.herokuapp.com",
    ".lqd2025-23ddd0fe8fa9.herokuapp.com",
    "localhost",
    "127.0.0.1",
]

# HTTPS settings
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Session settings for production
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# CSRF Configuration for production
CSRF_TRUSTED_ORIGINS = [
    'https://liquidateresina.com.br',
    'https://www.liquidateresina.com.br',
    'https://lqd2025-f3665d0be439.herokuapp.com',
    'https://lqd2024-ff3963465f8b.herokuapp.com',
    'https://lqd2025-23ddd0fe8fa9.herokuapp.com',
]

# Static files
STATICFILES_STORAGE = "liquida2018.storage_backends.StaticStorage"

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/tmp/django.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}
