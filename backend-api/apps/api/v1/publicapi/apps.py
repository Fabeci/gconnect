# publicapi/apps.py

from django.apps import AppConfig


class PublicapiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.api.v1.publicapi'
    label = 'publicapi'

    def ready(self):
        from . import signals  # noqa: F401
