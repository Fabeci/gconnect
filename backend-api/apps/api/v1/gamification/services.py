# gamification/services.py
"""Point d'entrée pour attribuer de l'XP et vérifier les badges."""
from django.db import models as django_models

from .models import Badge, UserBadge, UserGamificationProfile, XPEvent


def award_xp(user, amount, reason, *, check_badges=True):
    """Journalise un gain d'XP, incrémente le total en cache (F() — pas de
    read-then-write racy), puis vérifie les badges nouvellement débloqués."""
    XPEvent.objects.create(user=user, amount=amount, reason=reason)

    profile = UserGamificationProfile.for_user(user)
    UserGamificationProfile.objects.filter(pk=profile.pk).update(
        total_xp=django_models.F("total_xp") + amount
    )

    if check_badges:
        check_and_award_badges(user)


def _is_profile_complete(user):
    if not (user.bio and user.photo):
        return False
    profile = getattr(user, "student_profile", None) or getattr(user, "alumni_profile", None)
    if profile is None:
        return False
    return profile.interests.exists() and profile.skills.exists()


def _has_first_post(user):
    from apps.api.v1.posts.models import Post
    return Post.objects.filter(author=user, is_draft=False).exists()


def _post_count_at_least(user, n):
    from apps.api.v1.posts.models import Post
    return Post.objects.filter(author=user, is_draft=False).count() >= n


def _connections_at_least(user, n):
    from apps.api.v1.networking.models import Connection
    return len(Connection.connected_ids(user)) >= n


def _has_popular_post(user, min_reactions):
    from apps.api.v1.posts.models import Post
    from django.db.models import Count
    return Post.objects.filter(author=user).annotate(
        n=Count("reactions")
    ).filter(n__gte=min_reactions).exists()


# Registre {code_badge: callable(user) -> bool}. Ajouter un badge = ajouter
# une ligne ici + une ligne dans la migration de données `0002_seed_badges`.
BADGE_CRITERIA = {
    "profil_complet": _is_profile_complete,
    "premiere_publication": _has_first_post,
    "auteur_prolifique": lambda user: _post_count_at_least(user, 10),
    "reseauteur": lambda user: _connections_at_least(user, 10),
    "reseauteur_confirme": lambda user: _connections_at_least(user, 50),
    "publication_populaire": lambda user: _has_popular_post(user, 20),
}


def check_and_award_badges(user):
    """Vérifie les badges pas encore obtenus et attribue ceux dont le
    critère est rempli (+ bonus XP associé, sans redéclencher une passe de
    vérification pour éviter toute récursion)."""
    earned_codes = set(
        UserBadge.objects.filter(user=user).values_list("badge__code", flat=True)
    )
    newly_earned = []

    for code, check in BADGE_CRITERIA.items():
        if code in earned_codes:
            continue
        try:
            if check(user):
                newly_earned.append(code)
        except Exception:
            continue

    if not newly_earned:
        return []

    badges = {b.code: b for b in Badge.objects.filter(code__in=newly_earned)}
    awarded = []
    for code in newly_earned:
        badge = badges.get(code)
        if not badge:
            continue
        _, created = UserBadge.objects.get_or_create(user=user, badge=badge)
        if created:
            awarded.append(badge)
            if badge.xp_reward:
                award_xp(user, badge.xp_reward, "badge_bonus", check_badges=False)

    return awarded


def member_of_the_month(now=None):
    """Utilisateur ayant gagné le plus d'XP sur le mois calendaire en
    cours (ou `now`, pour les tests) — calculé à la demande, sans tâche
    planifiée (aucune infrastructure de scheduler dans ce projet)."""
    from django.contrib.auth import get_user_model
    from django.db.models import Sum
    from django.utils import timezone as dj_timezone

    now = now or dj_timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    top = (
        XPEvent.objects.filter(created_at__gte=month_start)
        .values("user_id")
        .annotate(month_xp=Sum("amount"))
        .order_by("-month_xp")
        .first()
    )
    if not top:
        return None, 0

    User = get_user_model()
    try:
        user = User.objects.get(id=top["user_id"])
    except User.DoesNotExist:
        return None, 0
    return user, top["month_xp"]
