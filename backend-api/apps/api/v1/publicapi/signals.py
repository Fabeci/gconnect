# publicapi/signals.py
"""Déclenchement passif des webhooks — écoute les signaux d'autres apps
sans les modifier (même pattern que gamification/notifications)."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.api.v1.networking.models import Connection
from apps.api.v1.posts.models import Post

from .models import WebhookSubscription
from .webhooks import trigger_webhook


@receiver(post_save, sender=Post)
def on_post_created(sender, instance, created, **kwargs):
    if not created or instance.is_draft:
        return
    trigger_webhook(
        WebhookSubscription.Event.POST_CREATED, instance.author,
        {"post_id": instance.id, "title": instance.title, "post_type": instance.post_type,
         "created_at": instance.created_at.isoformat()},
    )


@receiver(post_save, sender=Connection)
def on_connection_accepted(sender, instance, created, update_fields, **kwargs):
    if update_fields and 'status' in update_fields and instance.status == Connection.Status.ACCEPTED:
        for user in (instance.requester, instance.addressee):
            trigger_webhook(
                WebhookSubscription.Event.CONNECTION_ACCEPTED, user,
                {"connection_id": instance.id, "with_user_id": (
                    instance.addressee_id if user.id == instance.requester_id else instance.requester_id
                )},
            )
