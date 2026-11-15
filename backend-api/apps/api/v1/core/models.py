from django.conf import settings
from django.db import models
from django.utils import timezone
from rest_framework.authtoken.models import Token


class AuthTokenActivity(models.Model):
    """
    Dernière activité d'un jeton d'authentification — permet une expiration
    par inactivité (voir `ExpiringTokenAuthentication`) sans modifier le
    modèle `Token` de `rest_framework.authtoken`. Supprimé automatiquement
    quand le token est supprimé (logout, changement de mot de passe,
    révocation de sessions, suppression de compte).
    """
    token = models.OneToOneField(Token, on_delete=models.CASCADE, primary_key=True, related_name="activity")
    last_seen_at = models.DateTimeField()

    def __str__(self):
        return f"Activité de {self.token.user} — {self.last_seen_at}"


class AuditLogEntry(models.Model):
    """
    Journal d'audit des actions sensibles (connexion, changement de mot de
    passe, suppression de compte, révocation de sessions, modification de
    confidentialité, export RGPD, actions de modération à venir...).
    Écriture seule côté applicatif — consultable via l'admin Django en
    attendant l'écran back-office dédié (voir tâche V1.5 back-office).
    """
    ACTION_CHOICES = [
        ("login_success", "Connexion réussie"),
        ("login_failed", "Connexion échouée"),
        ("logout", "Déconnexion"),
        ("password_changed", "Mot de passe modifié"),
        ("sessions_revoked", "Sessions révoquées"),
        ("privacy_updated", "Confidentialité modifiée"),
        ("data_exported", "Données personnelles exportées"),
        ("account_deleted", "Compte supprimé"),
        ("report_reviewed", "Signalement examiné"),
        ("post_hidden", "Publication masquée par modération"),
        ("user_banned", "Utilisateur banni"),
        ("user_unbanned", "Utilisateur débanni"),
        ("import_completed", "Import massif effectué"),
        ("api_key_created", "Clé API créée"),
        ("api_key_revoked", "Clé API révoquée"),
        ("invitation_sent", "Invitation envoyée"),
        ("invitation_revoked", "Invitation révoquée"),
        ("invitation_accepted", "Invitation acceptée"),
        ("mfa_challenge_issued", "Contrôle MFA requis"),
        ("mfa_success", "Double authentification réussie"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="audit_log_entries",
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.get_action_display()} — {self.user} — {self.created_at}"


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Preference(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Sector(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Interest(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name