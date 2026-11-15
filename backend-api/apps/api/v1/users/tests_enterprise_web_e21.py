"""Enterprise web-console regression tests: MFA and strict company isolation."""
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory

from apps.api.v1.backoffice.views import AdminStatsView, EnterpriseDashboardView
from apps.api.v1.posts.models import Application, Opportunity, Post
from apps.api.v1.users.models import (
    Enterprise, EstablishmentWebSession, PrivilegedMFADevice, User,
)
from apps.api.v1.users.privileged_security import (
    encrypt_totp, generate_recovery_codes, generate_totp_secret,
)
from apps.api.v1.users.privileged_views import PrivilegedMFAVerifyView
from apps.api.v1.users.throttles import LoginThrottle, OtpThrottle
from apps.api.v1.users.views import MeView
from apps.api.v1.users.web_views import EstablishmentWebLoginView, EstablishmentWebResumeView


@override_settings(CORS_ALLOWED_ORIGINS=["http://127.0.0.1:8094"])
class EnterpriseWebConsoleTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.company_a_user = User.objects.create_user(
            username="company_a", email="company-a@example.test",
            password="E21-Company-Test-Password!", role="enterprise", is_active=True,
        )
        self.company_b_user = User.objects.create_user(
            username="company_b", email="company-b@example.test",
            password="E21-Company-Test-Password!", role="enterprise", is_active=True,
        )
        self.company_a = Enterprise.objects.create(
            verified_at=timezone.now(),
            user=self.company_a_user, company_name="Entreprise Alpha", sector="Tech",
        )
        self.company_b = Enterprise.objects.create(
            verified_at=timezone.now(),
            user=self.company_b_user, company_name="Entreprise Beta", sector="Conseil",
        )
        self.codes = {}
        for user in (self.company_a_user, self.company_b_user):
            PrivilegedMFADevice.objects.create(
                user=user,
                encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )
            self.codes[user.pk] = generate_recovery_codes(user)

    def web_login(self, user):
        request = self.factory.post(
            "/api/v1/users/web-login/",
            {"email": user.email, "password": "E21-Company-Test-Password!"},
            format="json", HTTP_USER_AGENT="Company web test",
        )
        with patch.object(LoginThrottle, "allow_request", return_value=True):
            challenge = EstablishmentWebLoginView.as_view()(request)
        self.assertEqual(challenge.status_code, 200)
        verify_request = self.factory.post(
            "/api/v1/users/web-mfa/verify/",
            {"challenge": challenge.data["data"]["challenge"],
             "code": self.codes[user.pk].pop(0)},
            format="json", HTTP_USER_AGENT="Company web test",
        )
        with patch.object(OtpThrottle, "allow_request", return_value=True):
            result = PrivilegedMFAVerifyView.as_view()(verify_request)
        self.assertEqual(result.status_code, 200)
        return result

    def web_request(self, view, raw, path="/api/v1/backoffice/enterprise-dashboard/"):
        request = self.factory.get(path, HTTP_AUTHORIZATION=f"WebToken {raw}")
        return view.as_view()(request)

    def test_mfa_cookie_resume_and_company_profile(self):
        verified = self.web_login(self.company_a_user)
        token = verified.data["data"]["token"]
        self.assertEqual(verified.data["data"]["role"], "enterprise")
        self.assertTrue(verified.cookies["gconnect_web_session"]["httponly"])
        resume = EstablishmentWebResumeView.as_view()(self.factory.post(
            "/api/v1/users/web-resume/", {}, format="json",
            HTTP_COOKIE=f"gconnect_web_session={token}",
            HTTP_ORIGIN="http://127.0.0.1:8094",
        ))
        self.assertEqual(resume.status_code, 200)
        self.assertEqual(resume.data["data"]["token"], token)
        me = self.web_request(MeView, token, "/api/v1/users/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["data"]["enterprise_id"], self.company_a.pk)
        self.assertEqual(me.data["data"]["company_name"], self.company_a.company_name)
        self.assertIsNone(me.data["data"]["institution_id"])
        self.assertEqual(EstablishmentWebSession.objects.filter(user=self.company_a_user).count(), 1)

    def test_enterprise_metrics_and_recent_offers_never_cross_company(self):
        post_a = Post.objects.create(
            author=self.company_a_user, title="Offre Alpha",
            post_type=Post.PostType.OPPORTUNITY,
        )
        opp_a = Opportunity.objects.create(
            post=post_a, enterprise=self.company_a,
            category=Opportunity.Category.JOB, status=Opportunity.Status.OPEN,
            contract_type=Opportunity.ContractType.PERMANENT,
        )
        post_b = Post.objects.create(
            author=self.company_b_user, title="Offre strictement Beta",
            post_type=Post.PostType.OPPORTUNITY,
        )
        opp_b = Opportunity.objects.create(
            post=post_b, enterprise=self.company_b,
            category=Opportunity.Category.JOB, status=Opportunity.Status.CLOSED,
            contract_type=Opportunity.ContractType.PERMANENT,
        )
        # A mismatched author must NOT grant Company A access to Company B's offers.
        cross_post = Post.objects.create(
            author=self.company_a_user, title="Beta-linked private offer",
            post_type=Post.PostType.OPPORTUNITY,
        )
        cross_offer = Opportunity.objects.create(
            post=cross_post, enterprise=self.company_b,
            category=Opportunity.Category.JOB, status=Opportunity.Status.OPEN,
            contract_type=Opportunity.ContractType.PERMANENT,
        )
        candidate = User.objects.create_user(
            username="candidate_e21", email="candidate@example.test",
            password="Candidate-Secure-Test!", role="student", is_active=True,
        )
        Application.objects.create(user=candidate, opportunity=opp_a)
        other_candidate = User.objects.create_user(
            username="other_e21", email="other-candidate@example.test",
            password="Candidate-Secure-Test!", role="student", is_active=True,
        )
        Application.objects.create(user=other_candidate, opportunity=opp_b)
        Application.objects.create(user=candidate, opportunity=cross_offer)

        token_a = self.web_login(self.company_a_user).data["data"]["token"]
        token_b = self.web_login(self.company_b_user).data["data"]["token"]
        response_a = self.web_request(EnterpriseDashboardView, token_a)
        response_b = self.web_request(EnterpriseDashboardView, token_b)
        self.assertEqual(response_a.status_code, 200)
        self.assertEqual(response_b.status_code, 200)
        a = response_a.data["data"]
        b = response_b.data["data"]
        self.assertEqual(a["scope"], "enterprise")
        self.assertEqual(a["enterprise_id"], self.company_a.pk)
        self.assertEqual(b["enterprise_id"], self.company_b.pk)
        self.assertEqual(a["opportunities"]["total"], 1)
        self.assertEqual(a["opportunities"]["open"], 1)
        self.assertEqual(b["opportunities"]["closed"], 1)
        self.assertEqual(b["opportunities"]["total"], 2)
        self.assertEqual(a["applications"]["total"], 1)
        self.assertEqual(b["applications"]["total"], 2)
        self.assertEqual(a["opportunities"]["recent"][0]["title"], "Offre Alpha")
        self.assertNotIn("Offre strictement Beta", str(a))
        self.assertNotIn("Beta-linked private offer", str(a))
        self.assertNotIn("candidate@example.test", str(a))
        self.assertEqual(a["applications"]["by_status"]["submitted"], 1)
        self.assertEqual(
            self.web_request(AdminStatsView, token_a, "/api/v1/backoffice/stats/").status_code,
            403,
        )

    def test_mobile_tokens_and_non_company_roles_cannot_use_company_dashboard(self):
        mobile_token = Token.objects.create(user=self.company_a_user)
        request = self.factory.get(
            "/api/v1/backoffice/enterprise-dashboard/",
            HTTP_AUTHORIZATION=f"Token {mobile_token.key}",
        )
        self.assertIn(
            EnterpriseDashboardView.as_view()(request).status_code, (401, 403),
        )
        super_user = User.objects.create_user(
            username="not_company_e21", email="platform-e21@example.test",
            password="E21-Company-Test-Password!", role="superAdmin", is_active=True,
        )
        PrivilegedMFADevice.objects.create(
            user=super_user,
            encrypted_secret=encrypt_totp(generate_totp_secret()),
            confirmed_at=timezone.now(),
        )
        session, raw = EstablishmentWebSession.issue(super_user, self.factory.get("/"))
        self.assertIsNotNone(session.pk)
        self.assertEqual(self.web_request(EnterpriseDashboardView, raw).status_code, 403)

    def test_missing_company_profile_cannot_enter_privileged_web_login(self):
        orphan = User.objects.create_user(
            username="orphan_company_e21", email="orphan-company@example.test",
            password="E21-Company-Test-Password!", role="enterprise", is_active=True,
        )
        request = self.factory.post(
            "/api/v1/users/web-login/",
            {"email": orphan.email, "password": "E21-Company-Test-Password!"},
            format="json",
        )
        with patch.object(LoginThrottle, "allow_request", return_value=True):
            result = EstablishmentWebLoginView.as_view()(request)
        self.assertEqual(result.status_code, 403)
        self.assertFalse(EstablishmentWebSession.objects.filter(user=orphan).exists())
