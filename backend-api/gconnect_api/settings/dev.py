# dev.py
from .base import *
import os

DEBUG = True
ALLOWED_HOSTS = ['*']

# Base de données SQLite pour dev.
# Un chemin explicite permet les essais web sur une base jetable séparée,
# sans toucher au db.sqlite3 déjà présent dans le dépôt partagé.
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.environ.get('GCONNECT_DEV_DB_PATH') or BASE_DIR / 'db.sqlite3',
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.getenv('POSTGRES_DB', 'gconnect'),
#         'USER': os.getenv('POSTGRES_USER', 'gconnect_user'),
#         'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'gconnect_pass'),
#         'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
#         'PORT': '5432',
#     }
# }

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'gconnect_db',
#         'USER': 'gconnect_user',
#         'PASSWORD': 'gconnect_pass',
#         'HOST': '127.0.0.1',  # ✅ Nom du service PostgreSQL dans docker-compose.yml
#         'PORT': '5432',
#     }
# }


# Django Debug Toolbar (optionnel)
INSTALLED_APPS += [
    # 'debug_toolbar',
]

MIDDLEWARE += [
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
]

# Pour REST API
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
        'login': '10/min',
        'otp': '5/min',
        'otp_resend': '3/min',
        'forgot_password': '3/min',
        'registration': '5/min',
    },
    'EXCEPTION_HANDLER': 'apps.api.v1.core.responses.custom_exception_handler',
}


# Les liens d'invitation E54 en développement doivent pointer sur le portail actif.
# En production, la configuration HTTPS explicite de base.py reste obligatoire.
GCONNECT_WEB_APP_URL = os.environ.get('GCONNECT_WEB_APP_URL', 'http://127.0.0.1:5173').rstrip('/')

# Email : console par défaut (affiche les emails dans le terminal).
# Pour tester avec un vrai Gmail, créer un fichier .env avec :
#   EMAIL_HOST_USER=votre@gmail.com
#   EMAIL_HOST_PASSWORD=votre-app-password-16-chars
# Puis remplacer EMAIL_BACKEND par 'django.core.mail.backends.smtp.EmailBackend'.
_email_host_user = os.environ.get('EMAIL_HOST_USER', '')

if _email_host_user:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.gmail.com'
    EMAIL_USE_TLS = True
    EMAIL_PORT = 587
    EMAIL_HOST_USER = _email_host_user
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', _email_host_user)
else:
    # Aucune credential SMTP configurée → afficher les emails dans le terminal.
    # Le code OTP sera visible dans les logs du serveur Django.
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_HOST_USER = 'noreply@gconnect.local'
    DEFAULT_FROM_EMAIL = 'noreply@gconnect.local'



AUTH_USER_MODEL = 'users.User'

# Local static previews of the web Establishment frontend (development only).
# The production CORS configuration is deliberately unchanged.
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'http://localhost:8086',
    'http://127.0.0.1:8086',
    'http://localhost:8094',
    'http://127.0.0.1:8094',
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
