"""
G-Connect - Notifications Signals
Génère automatiquement une notification quand un événement pertinent se
produit ailleurs dans l'application. Écoute passive (post_save) : aucun code
des autres apps n'est modifié, donc aucun risque de régression sur les vues
existantes de messagerie, relations, réactions ou commentaires.
"""
import re
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.api.v1.networking.models import Connection, Follow
from apps.api.v1.messaging.models import Message, ConversationParticipant
from apps.api.v1.posts.models import Reaction, Comment, Post, Application

from .models import Notification, NotificationPreference
from .push import send_push_notification


def _pref(user):
    return NotificationPreference.for_user(user)


def _create(recipient, actor, notification_type, verb, target_type=None, target_id=None):
    if actor is not None and actor_id_equals_recipient(actor, recipient):
        return  # jamais de notification pour soi-même
    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        verb=verb,
        target_type=target_type or "",
        target_id=target_id,
    )
    send_push_notification(notification)


def actor_id_equals_recipient(actor, recipient):
    return actor.id == recipient.id


# ── Relations (networking) ───────────────────────────────────────────────────

@receiver(post_save, sender=Connection)
def notify_connection_change(sender, instance, created, **kwargs):
    if created:
        if _pref(instance.addressee).connections_enabled:
            _create(
                recipient=instance.addressee, actor=instance.requester,
                notification_type=Notification.NotificationType.CONNECTION_REQUEST,
                verb="vous a envoyé une demande de connexion",
                target_type="connection", target_id=instance.id,
            )
    elif instance.status == Connection.Status.ACCEPTED and instance.responded_at is not None:
        if _pref(instance.requester).connections_enabled:
            _create(
                recipient=instance.requester, actor=instance.addressee,
                notification_type=Notification.NotificationType.CONNECTION_ACCEPTED,
                verb="a accepté votre demande de connexion",
                target_type="connection", target_id=instance.id,
            )


@receiver(post_save, sender=Follow)
def notify_new_follower(sender, instance, created, **kwargs):
    if created and _pref(instance.following).connections_enabled:
        _create(
            recipient=instance.following, actor=instance.follower,
            notification_type=Notification.NotificationType.NEW_FOLLOWER,
            verb="a commencé à vous suivre",
            target_type="user", target_id=instance.follower_id,
        )


# ── Messagerie ────────────────────────────────────────────────────────────────

@receiver(post_save, sender=Message)
def notify_new_message(sender, instance, created, **kwargs):
    if not created or instance.is_deleted or instance.sender is None:
        return

    # Requête directe sur ConversationParticipant (évite l'accès à
    # instance.conversation qui déclencherait une requête séparée).
    participants = list(
        ConversationParticipant.objects.filter(
            conversation_id=instance.conversation_id
        ).exclude(user=instance.sender).select_related("user")
    )
    if not participants:
        return

    # Batch-load des préférences pour éviter N+1 dans la boucle.
    user_ids = [p.user_id for p in participants]
    prefs_map = {
        pref.user_id: pref
        for pref in NotificationPreference.objects.filter(user_id__in=user_ids)
    }

    for participant in participants:
        pref = prefs_map.get(participant.user_id)
        # Pas de ligne = préférences par défaut (messages_enabled=True).
        if pref is None or pref.messages_enabled:
            _create(
                recipient=participant.user, actor=instance.sender,
                notification_type=Notification.NotificationType.NEW_MESSAGE,
                verb="vous a envoyé un message",
                target_type="conversation", target_id=instance.conversation_id,
            )


# ── Publications ──────────────────────────────────────────────────────────────

@receiver(post_save, sender=Reaction)
def notify_post_reaction(sender, instance, created, **kwargs):
    if not created:
        return
    author = instance.post.author
    if author and _pref(author).reactions_enabled:
        _create(
            recipient=author, actor=instance.user,
            notification_type=Notification.NotificationType.POST_REACTION,
            verb="a réagi à votre publication",
            target_type="post", target_id=instance.post_id,
        )


@receiver(post_save, sender=Comment)
def notify_post_comment(sender, instance, created, **kwargs):
    if not created:
        return

    # Réponse à un commentaire → notifier l'auteur du commentaire parent.
    if instance.parent_id and instance.parent.user:
        parent_author = instance.parent.user
        if _pref(parent_author).comments_enabled:
            _create(
                recipient=parent_author, actor=instance.user,
                notification_type=Notification.NotificationType.COMMENT_REPLY,
                verb="a répondu à votre commentaire",
                target_type="post", target_id=instance.post_id,
            )

    # Toujours notifier l'auteur du post (sauf s'il est aussi l'auteur du
    # parent — déjà notifié ci-dessus — pour éviter un doublon).
    author = instance.post.author
    already_notified_as_parent_author = instance.parent_id and instance.parent.user_id == getattr(author, "id", None)
    if author and not already_notified_as_parent_author and _pref(author).comments_enabled:
        _create(
            recipient=author, actor=instance.user,
            notification_type=Notification.NotificationType.POST_COMMENT,
            verb="a commenté votre publication",
            target_type="post", target_id=instance.post_id,
        )

    # Mentions dans le commentaire
    _notify_mentions(instance.content, actor=instance.user,
                     target_type="post", target_id=instance.post_id,
                     exclude_ids={instance.post.author_id})


# ── Candidatures ──────────────────────────────────────────────────────────────

@receiver(post_save, sender=Application)
def notify_new_application(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        author = instance.opportunity.post.author
    except Exception:
        return
    if author and _pref(author).reactions_enabled:
        _create(
            recipient=author,
            actor=instance.user,
            notification_type=Notification.NotificationType.APPLICATION,
            verb="a postulé à votre opportunité",
            target_type="opportunity",
            target_id=instance.opportunity_id,
        )


# ── Mentions ──────────────────────────────────────────────────────────────────

@receiver(post_save, sender=Post)
def notify_mentions_in_post(sender, instance, created, **kwargs):
    if not created:
        return
    _notify_mentions(instance.content, actor=instance.author,
                     target_type="post", target_id=instance.id)


def _notify_mentions(text, actor, target_type, target_id, exclude_ids=None):
    """Détecte les @username dans `text` et crée une notification MENTION."""
    if not text:
        return
    usernames = set(re.findall(r'@(\w+)', text))
    if not usernames:
        return
    User = get_user_model()
    qs = User.objects.filter(username__in=usernames)
    if actor:
        qs = qs.exclude(id=actor.id)
    if exclude_ids:
        qs = qs.exclude(id__in=exclude_ids)
    for user in qs:
        if _pref(user).comments_enabled:
            _create(
                recipient=user, actor=actor,
                notification_type=Notification.NotificationType.MENTION,
                verb="vous a mentionné dans une publication",
                target_type=target_type, target_id=target_id,
            )
