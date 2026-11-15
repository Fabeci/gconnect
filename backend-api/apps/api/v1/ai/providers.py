# ai/providers.py
"""
Interface fournisseur IA "pluggable" : `AIProvider` définit le contrat,
`get_ai_provider()` instancie l'implémentation configurée via le setting
`AI_PROVIDER` (défaut : `"rule_based"`). Brancher un vrai LLM (Anthropic,
OpenAI...) plus tard ne demande que d'implémenter `AIProvider` et de
changer ce setting — aucun autre code (vues, frontend) n'a besoin de
changer.

Honnêteté de périmètre : aucune clé API LLM n'est configurée dans cet
environnement. `RuleBasedAIProvider` est une implémentation RÉELLE (pas un
mock) mais à base de règles simples (fréquence de mots, troncature de
phrases) — elle fonctionne réellement, mais n'a pas la qualité d'un LLM.
"""
import re
from abc import ABC, abstractmethod

from django.conf import settings

_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "en", "à", "au", "aux",
    "ce", "ces", "cet", "cette", "que", "qui", "quoi", "pour", "par", "sur", "dans",
    "avec", "sans", "est", "sont", "être", "avoir", "il", "elle", "ils", "elles",
    "je", "tu", "nous", "vous", "on", "ne", "pas", "plus", "moins", "très", "tout",
    "tous", "toute", "toutes", "se", "sa", "son", "ses", "leur", "leurs", "mais",
    "ou", "où", "donc", "or", "ni", "car", "the", "and", "for", "with", "this",
}


class AIProvider(ABC):
    @abstractmethod
    def suggest_hashtags(self, text: str, max_tags: int = 5) -> list[str]:
        ...

    @abstractmethod
    def summarize(self, text: str, max_sentences: int = 2) -> str:
        ...

    @abstractmethod
    def improve_writing(self, text: str) -> dict:
        """Retourne {'suggestions': [str, ...]} — conseils, pas une réécriture
        automatique (voir limite de portée ci-dessus)."""
        ...

    @abstractmethod
    def recommend_posts(self, user, limit: int = 10):
        """Retourne un queryset/liste de `Post` recommandés à `user`."""
        ...


class RuleBasedAIProvider(AIProvider):
    """Implémentation sans dépendance externe, sans appel réseau — sert de
    fournisseur par défaut et de point de bascule vers un vrai LLM."""

    def _words(self, text: str) -> list[str]:
        return re.findall(r"[A-Za-zÀ-ÿ]{3,}", text.lower())

    def suggest_hashtags(self, text: str, max_tags: int = 5) -> list[str]:
        words = [w for w in self._words(text) if w not in _STOPWORDS]
        freq: dict[str, int] = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        ranked = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))
        return [f"#{w.capitalize()}" for w, _ in ranked[:max_tags]]

    def summarize(self, text: str, max_sentences: int = 2) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        sentences = [s for s in sentences if s]
        if not sentences:
            return ""
        return " ".join(sentences[:max_sentences])

    def improve_writing(self, text: str) -> dict:
        suggestions = []
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s]

        long_sentences = [s for s in sentences if len(s.split()) > 30]
        if long_sentences:
            suggestions.append(
                f"{len(long_sentences)} phrase(s) dépassent 30 mots — envisagez de les scinder pour plus de clarté."
            )
        if "  " in text:
            suggestions.append("Des espaces multiples ont été détectés — vérifiez la mise en forme.")
        if text and not text.strip()[-1:] in ".!?":
            suggestions.append("Le texte ne se termine pas par une ponctuation finale.")
        if len(text) > 0 and sum(1 for c in text if c.isupper()) / max(len(text), 1) > 0.3:
            suggestions.append("Beaucoup de majuscules — vérifiez que ce n'est pas perçu comme un cri.")
        if not suggestions:
            suggestions.append("Aucune amélioration évidente détectée — le texte semble clair.")

        return {"suggestions": suggestions}

    def recommend_posts(self, user, limit: int = 10):
        """Recommandation par recoupement de centres d'intérêt/secteurs —
        même esprit que le moteur de suggestions de relations
        (apps/api/v1/networking/suggestions.py) : tout précalculé en
        requêtes groupées, jamais une requête par candidat."""
        from django.db.models import Q
        from apps.api.v1.posts.models import Post

        interest_ids, sector_ids = set(), set()
        if hasattr(user, "student_profile"):
            interest_ids = set(user.student_profile.interests.values_list("id", flat=True))
            sector_ids = set(user.student_profile.sectors.values_list("id", flat=True))
        elif hasattr(user, "alumni_profile"):
            interest_ids = set(user.alumni_profile.interests.values_list("id", flat=True))
            sector_ids = set(user.alumni_profile.sectors.values_list("id", flat=True))

        base = Post.objects.filter(
            is_archived=False, is_draft=False, is_hidden_by_admin=False, audience=Post.Audience.PUBLIC,
        ).exclude(author=user).select_related("author").order_by("-created_at")

        if not interest_ids and not sector_ids:
            return list(base[:limit])

        matched = base.filter(
            Q(author__student_profile__interests__id__in=interest_ids) |
            Q(author__student_profile__sectors__id__in=sector_ids) |
            Q(author__alumni_profile__interests__id__in=interest_ids) |
            Q(author__alumni_profile__sectors__id__in=sector_ids)
        ).distinct()[:limit]
        matched = list(matched)

        if len(matched) < limit:
            seen_ids = {p.id for p in matched}
            filler = [p for p in base[: limit * 2] if p.id not in seen_ids][: limit - len(matched)]
            matched.extend(filler)

        return matched


_PROVIDERS = {
    "rule_based": RuleBasedAIProvider,
}


def get_ai_provider() -> AIProvider:
    name = getattr(settings, "AI_PROVIDER", "rule_based")
    provider_class = _PROVIDERS.get(name, RuleBasedAIProvider)
    return provider_class()
