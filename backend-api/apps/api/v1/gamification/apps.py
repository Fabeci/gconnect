# gamification/apps.py

from django.apps import AppConfig


class GamificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.api.v1.gamification'

    def ready(self):
        from . import signals  # noqa: F401
