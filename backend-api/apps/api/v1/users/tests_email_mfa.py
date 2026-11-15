"""Regression tests for the optional email-based professional second factor."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .email_mfa import (
    EmailMFADeliveryError, email_code, email_mfa_enabled,
    send_email_code, verify_email_code,
)
from .models import PrivilegedAuthChallenge


@override_settings(
    SECRET_KEY="email-otp-test-signing-key",
    GCONNECT_EMAIL_MFA_ENABLED=True,
    GCONNECT_EMAIL_MFA_API_KEY="unit-test-api-key",
    GCONNECT_EMAIL_MFA_FROM="G-Connect <no-reply@example.com>",
    GCONNECT_EMAIL_MFA_ALLOWED_EMAILS="account@example.com,email_mfa_test@example.com",
)
class EmailMFAUtilityTests(SimpleTestCase):
    def setUp(self):
        self.challenge = SimpleNamespace(
            token_hash="a" * 64,
            kind=PrivilegedAuthChallenge.KIND_VERIFY,
            KIND_VERIFY=PrivilegedAuthChallenge.KIND_VERIFY,
            expires_at=timezone.now() + timezone.timedelta(minutes=5),
            consumed_at=None,
            user_id=5,
        )

    def test_code_is_six_digits_challenge_bound_and_short_lived(self):
        code = email_code(self.challenge)
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())
        self.assertTrue(verify_email_code(self.challenge, code))
        self.assertFalse(verify_email_code(self.challenge, "not-code"))
        self.challenge.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        self.assertFalse(verify_email_code(self.challenge, code))

    def test_consumed_code_cannot_be_reused(self):
        code = email_code(self.challenge)
        self.challenge.consumed_at = timezone.now()
        self.assertFalse(verify_email_code(self.challenge, code))

    @patch("apps.api.v1.users.email_mfa.requests.post")
    def test_sends_only_via_https_to_account_email(self, send):
        send.return_value = Mock(status_code=200)
        send.return_value.json.return_value = {"id": "msg_example"}
        user = SimpleNamespace(pk=5, email="account@example.com")
        self.assertTrue(send_email_code(user, self.challenge))
        args, kwargs = send.call_args
        self.assertEqual(args[0], "https://api.resend.com/emails")
        self.assertEqual(kwargs["json"]["to"], ["account@example.com"])
        self.assertIn(email_code(self.challenge), kwargs["json"]["text"])
        self.assertNotIn(email_code(self.challenge), str(kwargs["headers"]))

    @patch("apps.api.v1.users.email_mfa.requests.post")
    def test_failed_delivery_is_rejected(self, send):
        send.return_value = Mock(status_code=403)
        user = SimpleNamespace(pk=5, email="account@example.com")
        with self.assertRaises(EmailMFADeliveryError):
            send_email_code(user, self.challenge)

    @override_settings(GCONNECT_EMAIL_MFA_ENABLED=False)
    def test_off_switch_rejects_all_email_codes(self):
        self.assertFalse(email_mfa_enabled())
        self.assertFalse(verify_email_code(self.challenge, email_code(self.challenge)))


@override_settings(
    SECRET_KEY="email-otp-test-signing-key",
    GCONNECT_EMAIL_MFA_ENABLED=True,
    GCONNECT_EMAIL_MFA_API_KEY="unit-test-api-key",
    GCONNECT_EMAIL_MFA_FROM="G-Connect <no-reply@example.com>",
)
class EmailMFALoginTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="email_mfa_superadmin",
            email="email_mfa_test@example.com",
            password="Secure_Test_Password_3901",
            role="superAdmin",
        )

    @patch("apps.api.v1.users.web_views.send_email_code", return_value=True)
    def test_login_creates_no_session_before_correct_otp(self, send):
        response = self.client.post(
            "/api/v1/users/web-login/",
            {"email": self.user.email, "password": "Secure_Test_Password_3901"},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["mfa_method"], "email")
        self.assertEqual(data["mfa_action"], "verify")
        self.assertNotIn("token", data)
        challenge = PrivilegedAuthChallenge.objects.get(user=self.user)
        send.assert_called_once()

        wrong = self.client.post(
            "/api/v1/users/web-mfa/verify/",
            {"challenge": data["challenge"], "code": "bad-code"},
            format="json",
        )
        self.assertEqual(wrong.status_code, 401)

        good = self.client.post(
            "/api/v1/users/web-mfa/verify/",
            {"challenge": data["challenge"], "code": email_code(challenge)},
            format="json",
        )
        self.assertEqual(good.status_code, 200, good.data)
        self.assertEqual(good.data["data"]["token_type"], "WebToken")
        self.assertEqual(good.data["data"]["role"], "superAdmin")

        replay = self.client.post(
            "/api/v1/users/web-mfa/verify/",
            {"challenge": data["challenge"], "code": email_code(challenge)},
            format="json",
        )
        self.assertEqual(replay.status_code, 401)

    @patch("apps.api.v1.users.web_views.send_email_code",
           side_effect=EmailMFADeliveryError("not sent"))
    def test_delivery_failure_does_not_create_usable_challenge(self, _send):
        response = self.client.post(
            "/api/v1/users/web-login/",
            {"email": self.user.email, "password": "Secure_Test_Password_3901"},
            format="json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertFalse(PrivilegedAuthChallenge.objects.filter(user=self.user).exists())
