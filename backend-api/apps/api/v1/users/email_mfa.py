"""One-time e-mail step-up for privileged G-Connect web sessions.

The 6-digit code is deterministically derived with HMAC from the *hashed*
pre-auth challenge and the server-only SECRET_KEY. No OTP is stored in clear
text or returned to the browser. The challenge lasts five minutes, limits
attempts, and is consumed before a WebToken is issued.
"""
import hashlib
import hmac
import json
import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class EmailMFADeliveryError(Exception):
    """Safe, non-sensitive delivery failure."""


def email_mfa_enabled():
    return (
        getattr(settings, "GCONNECT_EMAIL_MFA_ENABLED", False)
        and bool(getattr(settings, "GCONNECT_EMAIL_MFA_API_KEY", ""))
        and bool(getattr(settings, "GCONNECT_EMAIL_MFA_FROM", ""))
    )


def email_mfa_for_user(user):
    """Enabled only for explicitly permitted inboxes during the pilot.

    Never send to every privileged account using the Resend sandbox sender.
    After verifying a real sending domain, allowlisting can be expanded.
    """
    allowed = {
        email.strip().casefold()
        for email in getattr(settings, "GCONNECT_EMAIL_MFA_ALLOWED_EMAILS", "").split(",")
        if email.strip()
    }
    return (
        email_mfa_enabled()
        and bool(allowed)
        and bool(user.email)
        and user.email.strip().casefold() in allowed
    )


def email_code(challenge):
    """Derive a different unpredictable 6-digit value for each challenge."""
    payload = ("gconnect-email-otp-v1:" + challenge.token_hash).encode("ascii")
    digest = hmac.new(settings.SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).digest()
    return str(int.from_bytes(digest[:8], "big") % 1000000).zfill(6)


def verify_email_code(challenge, code):
    return bool(
        email_mfa_enabled()
        and challenge.kind == challenge.KIND_VERIFY
        and challenge.consumed_at is None
        and challenge.expires_at > timezone.now()
        and isinstance(code, str)
        and len(code) == 6
        and code.isascii()
        and code.isdecimal()
        and hmac.compare_digest(email_code(challenge), code)
    )


def send_email_code(user, challenge):
    """Send via a fixed HTTPS API on Render Free. Fail closed on any error."""
    if not email_mfa_for_user(user):
        raise EmailMFADeliveryError("Envoi e-mail indisponible pour ce compte.")
    if not user.email or challenge.user_id != user.pk:
        raise EmailMFADeliveryError("Adresse de destination invalide.")
    code = email_code(challenge)
    text = (
        "Votre code de connexion G-Connect : " + code + "\n\n"
        "Ce code expire dans 5 minutes. Ne le communiquez à personne.\n"
        "Si vous n'avez pas demandé cette connexion, ignorez cet e-mail."
    )
    payload = {
        "from": settings.GCONNECT_EMAIL_MFA_FROM,
        "to": [user.email],
        "subject": "G-Connect : votre code de connexion",
        "text": text,
    }
    headers = {
        "Authorization": "Bearer " + settings.GCONNECT_EMAIL_MFA_API_KEY,
        "Content-Type": "application/json",
        "User-Agent": "GConnect/2.0",
        "Idempotency-Key": "gconnect-login-" + challenge.token_hash[:44],
    }
    try:
        response = requests.post(
            "https://api.resend.com/emails",
            json=payload,
            headers=headers,
            timeout=8,
        )
        if response.status_code not in (200, 201):
            logger.warning("Email MFA provider rejected delivery: HTTP %d", response.status_code)
            raise EmailMFADeliveryError("Envoi e-mail indisponible.")
        if not response.json().get("id"):
            raise EmailMFADeliveryError("Confirmation d'envoi absente.")
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Email MFA delivery failed: %s", type(exc).__name__)
        raise EmailMFADeliveryError("Envoi e-mail indisponible.") from None
    return True
