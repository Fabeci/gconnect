"""Regression checks for encrypted MFA migrations between Django deployments."""
from unittest.mock import Mock

from django.test import SimpleTestCase, override_settings

from .privileged_security import _totp, decrypt_totp, encrypt_totp, verify_totp


class LegacyMFARotationTests(SimpleTestCase):
    SECRET = "JBSWY3DPEHPK3PXP"
    STEP = 1950000000 // 30

    def device(self):
        with override_settings(SECRET_KEY="old-development-key"):
            ciphertext = encrypt_totp(self.SECRET)
        return Mock(encrypted_secret=ciphertext, last_used_step=-1)

    def test_legacy_seed_is_rewrapped_after_valid_fresh_totp(self):
        device = self.device()
        code = _totp(self.SECRET, self.STEP)
        with override_settings(
            SECRET_KEY="new-production-key",
            GCONNECT_LEGACY_MFA_SECRET_KEY="old-development-key",
        ):
            self.assertEqual(
                verify_totp(device, code, at=self.STEP * 30), self.STEP
            )
            self.assertEqual(decrypt_totp(device.encrypted_secret), self.SECRET)
            device.save.assert_called_once_with(
                update_fields=["encrypted_secret", "updated_at"]
            )
        with override_settings(SECRET_KEY="new-production-key"):
            self.assertEqual(decrypt_totp(device.encrypted_secret), self.SECRET)

    def test_legacy_secret_unavailable_does_not_crash_login(self):
        device = self.device()
        code = _totp(self.SECRET, self.STEP)
        with override_settings(
            SECRET_KEY="new-production-key",
            GCONNECT_LEGACY_MFA_SECRET_KEY="",
        ):
            self.assertIsNone(verify_totp(device, code, at=self.STEP * 30))
            device.save.assert_not_called()

    def test_invalid_code_never_rewraps(self):
        device = self.device()
        original = device.encrypted_secret
        with override_settings(
            SECRET_KEY="new-production-key",
            GCONNECT_LEGACY_MFA_SECRET_KEY="old-development-key",
        ):
            self.assertIsNone(verify_totp(device, "not-a-code", at=self.STEP * 30))
            self.assertEqual(device.encrypted_secret, original)
            device.save.assert_not_called()
