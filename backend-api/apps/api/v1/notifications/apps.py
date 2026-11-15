# notifications/apps.py

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.api.v1.notifications'

    def ready(self):
        # Enregistre les signaux de génération automatique de notifications
        # (relations, messages, réactions, commentaires) sans toucher au code
        # des autres apps — purement passif, aucune régression possible sur
        # les vues existantes.
        from . import signals  # noqa: F401
