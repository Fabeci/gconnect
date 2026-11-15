# publicapi/webhooks.py
"""
Envoi des webhooks — livraison dans un thread d'arrière-plan (aucune file
de tâches/Celery dans ce projet, voir la même limite déjà documentée pour
les rappels de calendrier). Sans ça, un appel HTTP synchrone dans un
signal `post_save` bloquerait la réponse de l'utilisateur qui vient de
créer un post le temps que TOUS ses abonnements webhook répondent (jusqu'à
`_TIMEOUT_SECONDS` par abonnement) — inacceptable sur un chemin aussi
fréquent. Le thread est un pis-aller honnête : pas de persistance des
livraisons en attente ni de réessai si le processus redémarre en cours de
route ; une vraie file (Celery) serait nécessaire en production.

Le payload est signé en HMAC-SHA256 (en-tête X-GConnect-Signature) avec le
secret de l'abonnement, pour que le récepteur puisse vérifier
l'authenticité. Les échecs sont journalisés (last_status_code) mais jamais
réessayés automatiquement.
"""
import hashlib
import hmac
import json
import logging
import threading

import requests
from django.utils import timezone

from .models import WebhookSubscription

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 3


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _deliver(sub_id: int, event: str, body: bytes, secret: str, target_url: str):
    status_code = None
    try:
        resp = requests.post(
            target_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-GConnect-Signature": _sign(secret, body),
                "X-GConnect-Event": event,
            },
            timeout=_TIMEOUT_SECONDS,
        )
        status_code = resp.status_code
    except requests.RequestException as exc:
        logger.warning("Webhook delivery failed for subscription %s: %s", sub_id, exc)
    finally:
        WebhookSubscription.objects.filter(pk=sub_id).update(
            last_triggered_at=timezone.now(), last_status_code=status_code
        )


def trigger_webhook(event: str, user, payload: dict):
    """Envoie `payload` à tous les abonnements actifs de `user` pour `event`,
    chacun dans son propre thread — ne bloque jamais la requête appelante
    et ne lève jamais."""
    subscriptions = list(WebhookSubscription.objects.filter(user=user, event=event, is_active=True))
    if not subscriptions:
        return

    body = json.dumps({"event": event, "data": payload}).encode()
    for sub in subscriptions:
        threading.Thread(
            target=_deliver, args=(sub.id, event, body, sub.secret, sub.target_url), daemon=True,
        ).start()
