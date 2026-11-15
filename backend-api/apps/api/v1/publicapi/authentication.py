# publicapi/authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import ApiKey


class ApiKeyAuthentication(BaseAuthentication):
    """
    Authentification par clé API — pour les intégrations tierces, en plus
    du jeton de session utilisé par l'app mobile. En-tête attendu :
    `Authorization: ApiKey <clé>`. `request.auth` est l'instance `ApiKey`
    utilisée (les throttles s'en servent pour distinguer trafic API-clé vs
    trafic app mobile — voir throttling.py).
    """
    keyword = "ApiKey"

    def authenticate(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith(f"{self.keyword} "):
            return None

        raw_key = header[len(self.keyword) + 1:].strip()
        key = ApiKey.authenticate(raw_key)
        if not key:
            raise AuthenticationFailed("Clé API invalide ou révoquée.")
        if key.user.role in ("etablissement", "enterprise", "superAdmin"):
            raise AuthenticationFailed("Les clés API ne donnent pas accès aux espaces privilégiés.")

        return key.user, key
