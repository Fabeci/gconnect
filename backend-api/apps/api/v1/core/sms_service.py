import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(to: str, body: str) -> bool:
    """Envoie un SMS via Twilio. Retourne True si succès, False sinon."""
    sid   = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    from_ = getattr(settings, 'TWILIO_PHONE_NUMBER', '')

    if not all([sid, token, from_]):
        logger.error("Twilio non configuré (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_PHONE_NUMBER manquants)")
        return False

    try:
        from twilio.rest import Client
        client = Client(sid, token)
        client.messages.create(body=body, from_=from_, to=to)
        return True
    except Exception as exc:
        logger.error("Twilio send_sms error to %s: %s", to, exc)
        return False
