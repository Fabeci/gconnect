"""E3 regression tests for expiring and revoked legacy mobile-compatible tokens."""
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed

from apps.api.v1.core.authentication import ExpiringTokenAuthentication
from apps.api.v1.core.models import AuthTokenActivity
from apps.api.v1.users.models import User


class ExpiringTokenSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="security_e3", email="security-e3@example.test",
            password="strong-test-password", role="student", is_active=True,
        )
        self.token = Token.objects.create(user=self.user)
        self.auth = ExpiringTokenAuthentication()

    def test_valid_token_stays_compatible_with_existing_clients(self):
        user, token = self.auth.authenticate_credentials(self.token.key)
        self.assertEqual(user, self.user)
        self.assertEqual(token, self.token)

    def test_privileged_token_cannot_bypass_mfa(self):
        self.user.role = "etablissement"
        self.user.save(update_fields=["role"])
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate_credentials(self.token.key)

    def test_banned_user_token_is_revoked_at_authentication(self):
        self.user.is_banned = True
        self.user.save(update_fields=["is_banned"])
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate_credentials(self.token.key)
        self.assertFalse(Token.objects.filter(pk=self.token.pk).exists())

    @override_settings(AUTH_TOKEN_ABSOLUTE_TTL_DAYS=1)
    def test_expired_absolute_token_is_revoked(self):
        Token.objects.filter(pk=self.token.pk).update(
            created=timezone.now() - timedelta(days=2),
        )
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate_credentials(self.token.key)
        self.assertFalse(Token.objects.filter(pk=self.token.pk).exists())

    @override_settings(AUTH_TOKEN_IDLE_TTL_DAYS=1)
    def test_expired_idle_token_is_revoked(self):
        AuthTokenActivity.objects.create(
            token=self.token, last_seen_at=timezone.now() - timedelta(days=2),
        )
        with self.assertRaises(AuthenticationFailed):
            self.auth.authenticate_credentials(self.token.key)
        self.assertFalse(Token.objects.filter(pk=self.token.pk).exists())
