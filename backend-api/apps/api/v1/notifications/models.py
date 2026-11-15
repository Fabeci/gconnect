"""
G-Connect - Notifications Models
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class Notification(models.Model):
    """
    Notification in-app générique. `actor` est la personne à l'origine de
    l'événement (peut être null pour une notification système/rappel).
    `target_type`/`target_id` pointent vers l'objet concerné (post, message,
    connexion...) sans FK générique lourde (GenericForeignKey) — un simple
    couple type+id suffit pour construire le lien de navigation côté client.
    """

    class NotificationType(models.TextChoices):
        CONNECTION_REQUEST = "connection_request", "Nouvelle demande de connexion"
        CONNECTION_ACCEPTED = "connection_accepted", "Connexion acceptée"
        NEW_FOLLOWER = "new_follower", "Nouvel abonné"
        NEW_MESSAGE = "new_message", "Nouveau message"
        POST_REACTION = "post_reaction", "Réaction à une publication"
        POST_COMMENT = "post_comment", "Commentaire sur une publication"
        COMMENT_REPLY = "comment_reply", "Réponse à un commentaire"
        APPLICATION = "application", "Candidature reçue"
        MENTION = "mention", "Mention"
        SYSTEM = "system", "Système"

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    verb = models.CharField(max_length=255, blank=True)
    target_type = models.CharField(max_length=30, blank=True)
    target_id = models.PositiveIntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["recipient", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.notification_type}] -> {self.recipient.username}"


class NotificationPreference(models.Model):
    """Préférences de notification par utilisateur. `push_enabled`/
    `email_enabled` pilotent des canaux dont l'envoi effectif (FCM, SMTP)
    n'est pas encore branché — l'architecture est prête à les recevoir."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_preference")
    push_enabled = models.BooleanField(default=True)
    email_enabled = models.BooleanField(default=False)
    connections_enabled = models.BooleanField(default=True, verbose_name="Relations (demandes, abonnés)")
    messages_enabled = models.BooleanField(default=True, verbose_name="Messages")
    reactions_enabled = models.BooleanField(default=True, verbose_name="Réactions")
    comments_enabled = models.BooleanField(default=True, verbose_name="Commentaires")

    def __str__(self):
        return f"Préférences de {self.user.username}"

    @classmethod
    def for_user(cls, user):
        pref, _ = cls.objects.get_or_create(user=user)
        return pref


class DeviceToken(models.Model):
    """
    Jeton d'appareil pour les notifications push (FCM/APNs) — architecture
    prête, envoi non encore branché (voir `notifications/push.py`). Un même
    appareil (identifié par son jeton) ne doit être associé qu'à un seul
    utilisateur à la fois : à la ré-inscription sous un autre compte sur le
    même appareil, `register_token()` réattribue la ligne existante plutôt
    que d'en créer une seconde.
    """

    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"
        WEB = "web", "Web"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=10, choices=Platform.choices, default=Platform.ANDROID)
    created_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["user"])]

    def __str__(self):
        return f"{self.platform} token for {self.user.username}"

    @classmethod
    def register(cls, user, token, platform=Platform.ANDROID):
        obj, created = cls.objects.update_or_create(
            token=token, defaults={"user": user, "platform": platform, "last_seen_at": timezone.now()},
        )
        return obj, created
