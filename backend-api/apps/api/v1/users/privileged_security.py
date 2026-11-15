"""Enterprise privilege security: encrypted RFC 6238 TOTP and one-time challenges."""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from datetime import timedelta
from urllib.parse import quote, urlencode

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.utils import timezone

from .models import PrivilegedAuthChallenge, PrivilegedRecoveryCode

CHALLENGE_LIFETIME = timedelta(minutes=5)
MAX_CHALLENGE_FAILURES = 5
TOTP_PERIOD = 30


def token_digest(raw):
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _cipher(key=None):
    # Domain-separated derivation; SECRET_KEY must remain stable and private.
    secret = settings.SECRET_KEY if key is None else key
    source = ("gconnect-totp-v1:" + secret).encode("utf-8")
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(source).digest()))


def encrypt_totp(secret):
    return _cipher().encrypt(secret.encode("ascii")).decode("ascii")


def decrypt_totp(ciphertext):
    return _cipher().decrypt(ciphertext.encode("ascii")).decode("ascii")


def generate_totp_secret():
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def provisioning_uri(user, secret):
    label = "GConnect:" + user.email
    params = urlencode({"secret": secret, "issuer": "GConnect", "algorithm": "SHA1", "digits": 6, "period": 30})
    return "otpauth://totp/" + quote(label, safe="") + "?" + params


def _totp(secret, step):
    padded = secret + "=" * ((-len(secret)) % 8)
    key = base64.b32decode(padded, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1000000
    return str(value).zfill(6)


def verify_totp(device, code, *, at=None):
    """Return the accepted time step, never allow replay (even within drift)."""
    if not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isdigit():
        return None
    if not device.encrypted_secret:
        return None
    legacy = False
    try:
        secret = decrypt_totp(device.encrypted_secret)
    except (InvalidToken, ValueError, UnicodeError):
        # Imported TOTP seeds may have been encrypted by the original Django
        # key. Read the old key only from a temporarily configured secret.
        old_key = getattr(settings, "GCONNECT_LEGACY_MFA_SECRET_KEY", "")
        if not old_key or old_key == settings.SECRET_KEY:
            return None
        try:
            secret = _cipher(old_key).decrypt(
                device.encrypted_secret.encode("ascii")
            ).decode("ascii")
        except (InvalidToken, ValueError, UnicodeError):
            return None
        legacy = True
    current = int(time.time() if at is None else at) // TOTP_PERIOD
    for step in (current - 1, current, current + 1):
        if step > device.last_used_step and hmac.compare_digest(code, _totp(secret, step)):
            if legacy:
                # Rewrap only after a valid, fresh code. Keep the production
                # key unchanged. Remove the temporary legacy key afterward.
                device.encrypted_secret = encrypt_totp(secret)
                device.save(update_fields=["encrypted_secret", "updated_at"])
            return step
    return None


def issue_challenge(user, *, enroll):
    now = timezone.now()
    PrivilegedAuthChallenge.objects.filter(user=user, consumed_at__isnull=True).update(consumed_at=now)
    raw = secrets.token_urlsafe(36)
    PrivilegedAuthChallenge.objects.create(
        user=user, token_hash=token_digest(raw),
        kind=PrivilegedAuthChallenge.KIND_ENROLL if enroll else PrivilegedAuthChallenge.KIND_VERIFY,
        expires_at=now + CHALLENGE_LIFETIME,
    )
    return raw


def generate_recovery_codes(user):
    now = timezone.now()
    PrivilegedRecoveryCode.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    codes = ["-".join([value[i:i + 4] for i in range(0, 20, 4)])
             for value in (secrets.token_hex(10).upper() for _ in range(8))]
    PrivilegedRecoveryCode.objects.bulk_create([
        PrivilegedRecoveryCode(user=user, code_hash=token_digest(code.replace("-", "")))
        for code in codes
    ])
    return codes


def consume_recovery_code(user, code):
    normalized = str(code or "").strip().upper().replace("-", "")
    if len(normalized) != 20 or not normalized.isascii() or any(c not in "0123456789ABCDEF" for c in normalized):
        return False
    entry = PrivilegedRecoveryCode.objects.select_for_update().filter(
        user=user, code_hash=token_digest(normalized), used_at__isnull=True,
    ).first()
    if entry is None:
        return False
    entry.used_at = timezone.now()
    entry.save(update_fields=["used_at"])
    return True
