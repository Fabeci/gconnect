# base.py

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-change-this-key')
DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')

# Expiration des jetons d'authentification — voir apps/api/v1/core/authentication.py
AUTH_TOKEN_ABSOLUTE_TTL_DAYS = 90
AUTH_TOKEN_IDLE_TTL_DAYS = 30

# Privileged browser sessions are device-specific. The Flutter Token login is
# unchanged; these limits only apply to the opt-in /users/web-login/ flow.
ESTABLISHMENT_WEB_SESSION_HOURS = int(os.environ.get("GCONNECT_WEB_SESSION_HOURS", "12"))
ESTABLISHMENT_WEB_SESSION_IDLE_MINUTES = int(os.environ.get("GCONNECT_WEB_IDLE_MINUTES", "30"))
ESTABLISHMENT_WEB_SESSION_MAX_DEVICES = int(os.environ.get("GCONNECT_WEB_MAX_DEVICES", "5"))
# URL du frontend pour invitations par e-mail. HTTPS obligatoire hors debug.
GCONNECT_WEB_APP_URL = os.environ.get('GCONNECT_WEB_APP_URL', '').rstrip('/')

# Module IA pluggable — voir apps/api/v1/ai/providers.py. Aucune clé LLM
# n'est configurée dans cet environnement ; "rule_based" est un
# fournisseur réel (pas un mock) mais sans dépendance externe.
AI_PROVIDER = "rule_based"

INSTALLED_APPS = [
    'daphne',  # Doit être en premier pour le serveur ASGI WebSocket
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'django_extensions',
    'corsheaders',
    'apps.api.v1.core',
    'apps.api.v1.users',
    'apps.api.v1.establishments',
    'apps.api.v1.posts',
    'apps.api.v1.messaging',
    'apps.api.v1.networking',
    'apps.api.v1.notifications',
    'apps.api.v1.backoffice',
    'apps.api.v1.subscriptions',
    'apps.api.v1.gamification',
    'apps.api.v1.ai',
    'apps.api.v1.publicapi',
    'cities_light',
    'drf_yasg',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gconnect_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'gconnect_api.wsgi.application'
ASGI_APPLICATION = 'gconnect_api.asgi.application'

# Canal de couche — InMemory pour le dev (single-process).
# Remplacer par RedisChannelLayer en production :
#   pip install channels-redis
#   CHANNEL_LAYERS = {"default": {"BACKEND": "channels_redis.core.RedisChannelLayer",
#                                  "CONFIG": {"hosts": [("redis", 6379)]}}}
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

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

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

CITIES_LIGHT_TRANSLATION_LANGUAGES = ['fr']

CORS_ALLOWED_ORIGINS = []
CORS_ALLOW_CREDENTIALS = True

# ── Twilio SMS ─────────────────────────────────────────────────────────────────
TWILIO_ACCOUNT_SID  = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN   = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')
