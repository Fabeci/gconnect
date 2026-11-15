# gamification/signals.py
"""
Attribution passive d'XP — écoute les signaux d'autres apps (posts,
networking) sans jamais modifier leur code, même pattern déjà utilisé pour
les notifications (zéro risque de régression sur ces apps).
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.api.v1.networking.models import Connection
from apps.api.v1.posts.models import Post

from .models import XPEvent
from .services import award_xp


@receiver(post_save, sender=Post)
def on_post_saved(sender, instance, created, **kwargs):
    if not created or instance.is_draft:
        return
    is_first = Post.objects.filter(author=instance.author, is_draft=False).count() == 1
    if is_first:
        award_xp(instance.author, 20, XPEvent.Reason.FIRST_POST)
    else:
        award_xp(instance.author, 5, XPEvent.Reason.POST_CREATED)


@receiver(post_save, sender=Connection)
def on_connection_saved(sender, instance, created, update_fields, **kwargs):
    """`accept()` sauvegarde toujours avec update_fields=['status', ...] —
    sert de marqueur de transition pour ne récompenser qu'une fois."""
    if update_fields and 'status' in update_fields and instance.status == Connection.Status.ACCEPTED:
        award_xp(instance.requester, 10, XPEvent.Reason.CONNECTION_MADE)
        award_xp(instance.addressee, 10, XPEvent.Reason.CONNECTION_MADE)
