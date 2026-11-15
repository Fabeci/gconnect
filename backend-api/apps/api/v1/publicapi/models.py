# publicapi/models.py
"""
API publique : clés API (authentification alternative pour intégrations
tierces, en plus des jetons de session de l'app mobile) et abonnements
webhook. Le corps du texte clair d'une clé n'est JAMAIS stocké — seul son
hash (même principe que les mots de passe) ; la clé complète n'est montrée
qu'une fois, à la création (pattern "GitHub personal access token").
"""
import hashlib
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

_KEY_PREFIX = "gck_"  # "gconnect key"


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


class ApiKey(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="api_keys",
    )
    name = models.CharField(max_length=100, help_text="Nom donné par l'utilisateur (ex : 'Intégration CRM').")
    key_hash = models.CharField(max_length=64, unique=True, db_index=True)
    key_prefix = models.CharField(max_length=12, help_text="8 premiers caractères — affichés pour identifier la clé sans révéler le secret.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.key_prefix}…) — {self.user}"

    @classmethod
    def generate(cls, user, name: str):
        """Crée une nouvelle clé et retourne (instance, clé_en_clair). La
        clé en clair n'est disponible qu'à cet instant — elle n'est jamais
        récupérable ensuite."""
        raw_key = f"{_KEY_PREFIX}{secrets.token_urlsafe(32)}"
        instance = cls.objects.create(
            user=user, name=name,
            key_hash=_hash_key(raw_key),
            key_prefix=raw_key[:12],
        )
        return instance, raw_key

    @classmethod
    def authenticate(cls, raw_key: str):
        """Retourne l'ApiKey correspondante (active) ou None."""
        if not raw_key or not raw_key.startswith(_KEY_PREFIX):
            return None
        try:
            key = cls.objects.select_related("user").get(key_hash=_hash_key(raw_key), is_active=True)
        except cls.DoesNotExist:
            return None
        cls.objects.filter(pk=key.pk).update(last_used_at=timezone.now())
        return key


class WebhookSubscription(models.Model):
    class Event(models.TextChoices):
        POST_CREATED = "post.created", "Nouvelle publication"
        CONNECTION_ACCEPTED = "connection.accepted", "Relation acceptée"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="webhook_subscriptions",
    )
    target_url = models.URLField()
    event = models.CharField(max_length=40, choices=Event.choices)
    secret = models.CharField(max_length=64, default=secrets.token_hex, help_text="Utilisé pour signer le payload (en-tête X-GConnect-Signature).")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    last_status_code = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["event", "is_active"])]

    def __str__(self):
        return f"{self.get_event_display()} → {self.target_url}"
