# authentication.py
"""
Authentification par jeton avec expiration.

DRF `TokenAuthentication` standard n'expire jamais un token. Ici on ajoute
deux limites de sécurité, configurables via les settings :
- `AUTH_TOKEN_ABSOLUTE_TTL_DAYS` : âge maximal du token depuis sa création.
- `AUTH_TOKEN_IDLE_TTL_DAYS` : durée d'inactivité maximale avant expiration.

Au-delà, le token est supprimé et la requête est rejetée (401) — le client
doit se reconnecter (nouveau token émis par `LoginView`). L'activité est
suivie via `AuthTokenActivity`, mise à jour au plus une fois toutes les
5 minutes par token pour éviter une écriture DB à chaque requête.
"""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.api.v1.core.models import AuthTokenActivity

_ACTIVITY_WRITE_THROTTLE = timedelta(minutes=5)


class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        # Legacy Flutter Token remains for student/alumni accounts only;
        # privileged dashboards must pass the TOTP step-up flow.
        if user.role in ("etablissement", "enterprise", "superAdmin"):
            raise AuthenticationFailed("Connexion web avec double authentification requise.")
        if getattr(user, "is_banned", False):
            token.delete()
            raise AuthenticationFailed("Compte suspendu. Veuillez contacter l'administration.")
        now = timezone.now()

        absolute_ttl = timedelta(days=getattr(settings, "AUTH_TOKEN_ABSOLUTE_TTL_DAYS", 90))
        if now - token.created > absolute_ttl:
            token.delete()
            raise AuthenticationFailed("Session expirée. Veuillez vous reconnecter.")

        activity, created = AuthTokenActivity.objects.get_or_create(
            token=token, defaults={"last_seen_at": now}
        )
        if not created:
            idle_ttl = timedelta(days=getattr(settings, "AUTH_TOKEN_IDLE_TTL_DAYS", 30))
            if now - activity.last_seen_at > idle_ttl:
                token.delete()
                raise AuthenticationFailed("Session expirée par inactivité. Veuillez vous reconnecter.")

            if now - activity.last_seen_at > _ACTIVITY_WRITE_THROTTLE:
                activity.last_seen_at = now
                activity.save(update_fields=["last_seen_at"])

        return user, token
