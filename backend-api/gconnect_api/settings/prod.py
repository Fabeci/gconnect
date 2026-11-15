# prod.py
from .base import *
import os

DEBUG = False
# Fail closed on public deployment: require a unique secret and actual database.
SECRET_KEY = os.environ["SECRET_KEY"]
# Optional temporary key for re-encrypting imported 2FA secrets on verified login.
GCONNECT_LEGACY_MFA_SECRET_KEY = os.environ.get("GCONNECT_LEGACY_MFA_SECRET_KEY", "")
# Automatic email step-up is strictly opt-in. On Render Free, email travels
# through a verified HTTPS provider, never through blocked SMTP port 587.
GCONNECT_EMAIL_MFA_ENABLED = os.environ.get("GCONNECT_EMAIL_MFA_ENABLED", "false").lower() == "true"
GCONNECT_EMAIL_MFA_API_KEY = os.environ.get("RESEND_API_KEY", "")
GCONNECT_EMAIL_MFA_FROM = os.environ.get("GCONNECT_EMAIL_MFA_FROM", "")
GCONNECT_EMAIL_MFA_ALLOWED_EMAILS = os.environ.get("GCONNECT_EMAIL_MFA_ALLOWED_EMAILS", "")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
CSRF_TRUSTED_ORIGINS = [
    value.strip() for value in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if value.strip()
]
# Variable d'environnement CSV, ex: ALLOWED_HOSTS=app.gconnect.sn,www.gconnect.sn
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Exemple PostgreSQL (à adapter)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ['POSTGRES_DB'],
        'USER': os.environ['POSTGRES_USER'],
        'PASSWORD': os.environ['POSTGRES_PASSWORD'],
        'HOST': os.environ['POSTGRES_HOST'],
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'OPTIONS': {'sslmode': 'require'},
    }
}

# Sécurité en production
SECURE_HSTS_SECONDS = 3600
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = 'DENY'

# Logging (basique)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# CORS — variable d'environnement CSV, ex: CORS_ALLOWED_ORIGINS=https://app.gconnect.sn,https://www.gconnect.sn
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',')
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True

# REST API
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'apps.api.v1.users.web_authentication.EstablishmentWebTokenAuthentication',
        'apps.api.v1.core.authentication.ExpiringTokenAuthentication',
        'apps.api.v1.publicapi.authentication.ApiKeyAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'apps.api.v1.publicapi.throttling.ApiKeyRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'api_key': '1000/day',
        'login': '5/min',
        'otp': '5/min',
        'otp_resend': '2/min',
        'forgot_password': '2/min',
        'registration': '3/min',
    },
    'EXCEPTION_HANDLER': 'apps.api.v1.core.responses.custom_exception_handler',
}
