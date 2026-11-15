# gamification/models.py
"""
Gamification : points d'expérience (XP), niveaux, badges/trophées, membre du
mois. Le niveau se déduit de l'XP total par une formule simple et stable
(100 XP par niveau) plutôt que d'être stocké — une seule source de vérité.
Les trophées sont des badges de palier "or" (`Badge.tier`) : même mécanisme,
pas de modèle parallèle à maintenir.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

XP_PER_LEVEL = 100


def level_for_xp(xp: int) -> int:
    """Niveau 1 à 0 XP, +1 niveau tous les 100 XP."""
    return max(1, xp // XP_PER_LEVEL + 1)


def xp_progress(xp: int) -> dict:
    level = level_for_xp(xp)
    into_level = xp % XP_PER_LEVEL
    return {
        "level": level,
        "xp_total": xp,
        "xp_into_level": into_level,
        "xp_for_next_level": XP_PER_LEVEL,
    }


class UserGamificationProfile(models.Model):
    """XP total mis en cache (mis à jour via F() à chaque XPEvent) — évite
    de ré-agréger `XPEvent` à chaque affichage de profil."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="gamification_profile",
    )
    total_xp = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} — {self.total_xp} XP (niveau {level_for_xp(self.total_xp)})"

    @classmethod
    def for_user(cls, user):
        profile, _ = cls.objects.get_or_create(user=user)
        return profile


class XPEvent(models.Model):
    """Journal append-only des gains d'XP — source de vérité pour le
    classement mensuel ('membre du mois') et l'historique."""
    class Reason(models.TextChoices):
        PROFILE_COMPLETED = "profile_completed", "Profil complété"
        FIRST_POST = "first_post", "Première publication"
        POST_CREATED = "post_created", "Publication créée"
        CONNECTION_MADE = "connection_made", "Nouvelle relation"
        POPULAR_POST = "popular_post", "Publication populaire"
        BADGE_BONUS = "badge_bonus", "Bonus de badge"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="xp_events",
    )
    amount = models.PositiveIntegerField()
    reason = models.CharField(max_length=30, choices=Reason.choices)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"+{self.amount} XP ({self.get_reason_display()}) — {self.user}"


class Badge(models.Model):
    """Catalogue des badges/trophées disponibles — voir la migration de
    données `0002_seed_badges` pour le jeu de badges initial."""
    class Tier(models.TextChoices):
        BRONZE = "bronze", "Bronze"
        SILVER = "silver", "Argent"
        GOLD = "gold", "Or (trophée)"

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True, default="")
    icon_emoji = models.CharField(max_length=8, default="🏅")
    tier = models.CharField(max_length=10, choices=Tier.choices, default=Tier.BRONZE)
    xp_reward = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.icon_emoji} {self.name}"


class UserBadge(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="badges_earned",
    )
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name="earned_by")
    earned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "badge")
        ordering = ["-earned_at"]

    def __str__(self):
        return f"{self.user} — {self.badge.name}"
