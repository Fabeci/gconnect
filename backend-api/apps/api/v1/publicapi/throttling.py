# publicapi/throttling.py
from .models import ApiKey
from rest_framework.throttling import SimpleRateThrottle


class ApiKeyRateThrottle(SimpleRateThrottle):
    """
    Limite spécifiquement le trafic authentifié par clé API (intégrations
    tierces) — n'affecte pas le trafic de l'app mobile authentifié par
    jeton de session. Taux configuré via
    REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['api_key'] (voir settings).
    """
    scope = "api_key"

    def get_cache_key(self, request, view):
        if not isinstance(request.auth, ApiKey):
            return None  # pas authentifié par clé API : pas de limite ici
        return self.cache_format % {"scope": self.scope, "ident": request.auth.id}
