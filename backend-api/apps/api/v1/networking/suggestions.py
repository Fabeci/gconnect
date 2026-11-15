"""
G-Connect - Networking Suggestions
Moteur de recommandations de relations : établissement commun, promotion
commune, relations communes, centres d'intérêt/secteurs communs.

Toutes les jointures coûteuses (promotions des candidats, relations communes)
sont précalculées en requêtes groupées bornées — jamais une requête par
candidat — pour rester praticable même si le bassin de candidats grandit.
"""
from collections import defaultdict
from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.api.v1.establishments.models import (
    PromotionMembership, AlumniPromotionMembership, StudentInstitution, AlumniInstitution,
)
from .models import Connection

User = get_user_model()


def _profile_facets(user):
    """Établissements/promotions/intérêts/secteurs d'un utilisateur, quel que
    soit son profil (étudiant ou alumni). Établissements/promotions restreints
    à ceux marqués actifs (`is_active`) — le contexte actif de l'utilisateur
    pilote les recommandations, pas son historique complet d'affiliations."""
    institution_ids, promotion_ids, interest_ids, sector_ids = set(), set(), set(), set()

    if hasattr(user, "student_profile"):
        sp = user.student_profile
        institution_ids = set(
            StudentInstitution.objects.filter(student=sp, is_active=True).values_list("institution_id", flat=True)
        )
        promotion_ids = set(
            PromotionMembership.objects.filter(
                student=sp, is_approved=True, is_active=True
            ).values_list("promotion_id", flat=True)
        )
        interest_ids = {i.id for i in sp.interests.all()}
        sector_ids = {s.id for s in sp.sectors.all()}
    elif hasattr(user, "alumni_profile"):
        ap = user.alumni_profile
        institution_ids = set(
            AlumniInstitution.objects.filter(alumni=ap, is_active=True).values_list("institution_id", flat=True)
        )
        if not institution_ids and ap.institution_id:
            institution_ids = {ap.institution_id}
        promotion_ids = set(
            AlumniPromotionMembership.objects.filter(
                alumni=ap, is_approved=True, is_active=True
            ).values_list("promotion_id", flat=True)
        )
        if not promotion_ids and ap.promotion_id:
            promotion_ids = {ap.promotion_id}
        interest_ids = {i.id for i in ap.interests.all()}
        sector_ids = {s.id for s in ap.sectors.all()}

    return institution_ids, promotion_ids, interest_ids, sector_ids


def build_connection_suggestions(user, limit=10, pool_size=150):
    """Retourne jusqu'à `limit` tuples (score, user, raisons, breakdown) triés
    par pertinence décroissante. Un score de 0 (aucun point commun) est
    exclu. `breakdown` = {same_institution, same_promotion, mutual_count}
    pour piloter les filtres et l'affichage des relations mutuelles côté
    client, sans avoir à re-parser le texte de `raisons`."""
    my_connections = Connection.connected_ids(user)
    exclude_ids = {user.id} | my_connections

    pending_rows = Connection.objects.filter(
        Q(requester=user) | Q(addressee=user), status=Connection.Status.PENDING
    ).values_list("requester_id", "addressee_id")
    for a, b in pending_rows:
        exclude_ids.add(a)
        exclude_ids.add(b)

    my_institution_ids, my_promotion_ids, my_interest_ids, my_sector_ids = _profile_facets(user)

    candidates = list(
        User.objects.exclude(id__in=exclude_ids)
        .filter(Q(student_profile__isnull=False) | Q(alumni_profile__isnull=False))
        .select_related("student_profile", "alumni_profile")
        .prefetch_related(
            "student_profile__institutions", "student_profile__interests", "student_profile__sectors",
            "alumni_profile__interests", "alumni_profile__sectors",
        )
        .order_by("-date_joined")[:pool_size]
    )
    if not candidates:
        return []

    candidate_ids = [c.id for c in candidates]

    # Promotions des candidats étudiants — 1 requête groupée (pas une par candidat).
    student_candidate_ids = [c.student_profile.id for c in candidates if hasattr(c, "student_profile")]
    promo_by_student = defaultdict(set)
    if student_candidate_ids:
        for student_id, promotion_id in PromotionMembership.objects.filter(
            student_id__in=student_candidate_ids, is_approved=True
        ).values_list("student_id", "promotion_id"):
            promo_by_student[student_id].add(promotion_id)

    # Relations communes — 1 requête groupée couvrant mes relations + tous les candidats.
    relevant_ids = my_connections | set(candidate_ids)
    adjacency = defaultdict(set)
    if relevant_ids:
        for a, b in Connection.objects.filter(status=Connection.Status.ACCEPTED).filter(
            Q(requester_id__in=relevant_ids) | Q(addressee_id__in=relevant_ids)
        ).values_list("requester_id", "addressee_id"):
            adjacency[a].add(b)
            adjacency[b].add(a)

    scored = []
    for candidate in candidates:
        cand_institution_ids, cand_interest_ids, cand_sector_ids = set(), set(), set()
        cand_promotion_ids = set()

        if hasattr(candidate, "student_profile"):
            csp = candidate.student_profile
            cand_institution_ids = {i.id for i in csp.institutions.all()}
            cand_promotion_ids = promo_by_student.get(csp.id, set())
            cand_interest_ids = {i.id for i in csp.interests.all()}
            cand_sector_ids = {s.id for s in csp.sectors.all()}
        elif hasattr(candidate, "alumni_profile"):
            cap = candidate.alumni_profile
            if cap.institution_id:
                cand_institution_ids = {cap.institution_id}
            if cap.promotion_id:
                cand_promotion_ids = {cap.promotion_id}
            cand_interest_ids = {i.id for i in cap.interests.all()}
            cand_sector_ids = {s.id for s in cap.sectors.all()}

        score = 0
        reasons = []
        same_institution = bool(my_institution_ids & cand_institution_ids)
        same_promotion = bool(my_promotion_ids & cand_promotion_ids)

        if same_institution:
            score += 3
            reasons.append("même établissement")
        if same_promotion:
            score += 2
            reasons.append("même promotion")
        mutual_ids = my_connections & adjacency.get(candidate.id, set())
        mutual = len(mutual_ids)
        if mutual:
            score += min(mutual, 5) * 2
            reasons.append(f"{mutual} relation{'s' if mutual > 1 else ''} en commun")
        if my_interest_ids & cand_interest_ids:
            score += 1
            reasons.append("centres d'intérêt communs")
        if my_sector_ids & cand_sector_ids:
            score += 1
            reasons.append("même secteur")

        if score > 0:
            breakdown = {
                "same_institution": same_institution,
                "same_promotion": same_promotion,
                "mutual_count": mutual,
                "mutual_preview_ids": list(mutual_ids)[:3],
            }
            scored.append((score, candidate, " · ".join(reasons), breakdown))

    scored.sort(key=lambda row: -row[0])
    return scored[:limit]
