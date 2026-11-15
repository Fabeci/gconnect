"""E5.3 security tests: verified enterprises, invitations, tenant scope and MFA."""
import re
import time
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory

from apps.api.v1.posts.models import Application, Opportunity, Post
from apps.api.v1.users.enterprise_views import (
    EnterpriseDashboardView, EnterpriseInvitationAcceptView,
    EnterpriseInvitationPreviewView, EnterpriseInvitationRevokeView,
    EnterpriseOfferApplicationsView, EnterpriseOpportunitiesView,
    EnterpriseRecruiterInvitesView, EnterpriseRecruiterRevokeView,
    EnterpriseRecruitersView, SuperadminEnterpriseInvitesView,
)
from apps.api.v1.users.models import (
    Enterprise, EnterpriseInvitation, EnterpriseMember, EstablishmentWebSession,
    PrivilegedMFADevice, User,
)
from apps.api.v1.users.privileged_security import _totp, encrypt_totp, generate_totp_secret, token_digest
from apps.api.v1.users.privileged_views import PrivilegedMFASetupView, PrivilegedMFAVerifyView
from apps.api.v1.users.throttles import LoginThrottle, OtpThrottle, RegistrationThrottle
from apps.api.v1.users.views import GoogleLoginView, LoginView, MeView
from apps.api.v1.users.web_views import EstablishmentWebLoginView


@override_settings(
    DEBUG=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    GCONNECT_WEB_APP_URL="https://gconnect.example.test",
)
class EnterpriseSecurityE53Tests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.root = User.objects.create_user(
            username="e53_root", email="root-e53@example.test",
            password="Strong-Superadmin-E53!", role="superAdmin", is_active=True,
        )
        secret = generate_totp_secret()
        PrivilegedMFADevice.objects.create(
            user=self.root, encrypted_secret=encrypt_totp(secret), confirmed_at=timezone.now(),
        )
        _, self.root_token = EstablishmentWebSession.issue(self.root, self.factory.post("/"))
        self.student = User.objects.create_user(
            username="e53_student", email="student-e53@example.test",
            password="Strong-Student-E53!", role="student", is_active=True,
        )

    def call(self, view, path="/", method="post", token=None, scheme="WebToken", data=None, **kwargs):
        options = {"format": "json"}
        if token:
            options["HTTP_AUTHORIZATION"] = f"{scheme} {token}"
        request = getattr(self.factory, method)(path, data=data or {}, **options)
        with patch.object(RegistrationThrottle, "allow_request", return_value=True), \
             patch.object(LoginThrottle, "allow_request", return_value=True), \
             patch.object(OtpThrottle, "allow_request", return_value=True):
            return view.as_view()(request, **kwargs)

    def owner_invite(self, email="owner-e53@example.test", company="G-Connect Partners"):
        response = self.call(
            SuperadminEnterpriseInvitesView, token=self.root_token,
            data={"email": email, "company_name": company, "sector": "Technologie"},
        )
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        raw = re.search(r"#invitation=([A-Za-z0-9_-]+)", mail.outbox[-1].body).group(1)
        return response, raw

    def accept(self, raw, password="E53-Complex-Account!"):
        return self.call(EnterpriseInvitationAcceptView, data={
            "invitation": raw, "password": password, "first_name": "Awa", "last_name": "Diallo",
        })

    def login_and_mfa(self, email, password="E53-Complex-Account!"):
        start = self.call(EstablishmentWebLoginView, data={"email": email, "password": password})
        self.assertEqual(start.status_code, 200, getattr(start, "data", None))
        self.assertNotIn("token", start.data["data"])
        challenge = start.data["data"]["challenge"]
        setup = self.call(PrivilegedMFASetupView, data={"challenge": challenge})
        self.assertEqual(setup.status_code, 200, getattr(setup, "data", None))
        code = _totp(setup.data["data"]["secret"], int(time.time()) // 30)
        verified = self.call(PrivilegedMFAVerifyView, data={"challenge": challenge, "code": code})
        self.assertEqual(verified.status_code, 200, getattr(verified, "data", None))
        self.assertEqual(verified.data["data"]["token_type"], "WebToken")
        return verified.data["data"]["token"]

    def make_owner(self, email="owner-e53@example.test", company="G-Connect Partners"):
        _, raw = self.owner_invite(email, company)
        result = self.accept(raw)
        self.assertEqual(result.status_code, 200, getattr(result, "data", None))
        return User.objects.get(email=email)

    def test_superadmin_only_can_invite_owner_and_secret_is_never_returned(self):
        student_token = Token.objects.create(user=self.student)
        denied = self.call(
            SuperadminEnterpriseInvitesView, token=student_token.key, scheme="Token",
            data={"email": "a@example.test", "company_name": "Fake", "sector": "X"},
        )
        self.assertEqual(denied.status_code, 401)
        result, raw = self.owner_invite()
        self.assertNotIn(raw, str(result.data))
        entry = EnterpriseInvitation.objects.get(pk=result.data["data"]["id"])
        self.assertEqual(entry.kind, "owner")
        self.assertEqual(entry.token_hash, token_digest(raw))
        self.assertNotIn(raw, str(entry.__dict__))
        self.assertIn("entreprise-activation.html#invitation=", mail.outbox[-1].body)
        preview = self.call(EnterpriseInvitationPreviewView, data={"invitation": raw})
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.data["data"]["kind"], "owner")
        self.assertNotIn("invitation", preview.data["data"])

    def test_activation_confirms_email_and_creates_verified_company_once(self):
        _, raw = self.owner_invite()
        self.assertEqual(self.accept(raw, "123").status_code, 400)
        self.assertFalse(User.objects.filter(email="owner-e53@example.test").exists())
        self.assertEqual(self.accept(raw).status_code, 200)
        self.assertEqual(self.accept(raw).status_code, 400)
        user = User.objects.get(email="owner-e53@example.test")
        company = user.enterprise_profile
        self.assertEqual(company.company_name, "G-Connect Partners")
        self.assertIsNotNone(company.verified_at)
        self.assertTrue(company.is_active)
        self.assertFalse(Token.objects.filter(user=user).exists())

    def test_company_owner_must_complete_mfa_before_dashboard(self):
        self.make_owner()
        start = self.call(EstablishmentWebLoginView, data={
            "email": "owner-e53@example.test", "password": "E53-Complex-Account!",
        })
        self.assertEqual(start.status_code, 200)
        challenge = start.data["data"]["challenge"]
        self.assertEqual(self.call(EnterpriseDashboardView, token=challenge, method="get").status_code, 401)
        token = self.login_and_mfa("owner-e53@example.test")
        dashboard = self.call(EnterpriseDashboardView, token=token, method="get")
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data["data"]["membership"], "owner")
        self.assertEqual(dashboard.data["data"]["stats"]["opportunities"], 0)
        me = self.call(MeView, token=token, method="get")
        self.assertEqual(me.data["data"]["enterprise_id"], User.objects.get(email="owner-e53@example.test").enterprise_profile.pk)

    def test_expiration_revoke_and_failed_smtp_are_fail_closed(self):
        _, raw = self.owner_invite()
        invitation = EnterpriseInvitation.objects.get(token_hash=token_digest(raw))
        invitation.expires_at = timezone.now() - timedelta(seconds=1)
        invitation.save(update_fields=["expires_at"])
        self.assertEqual(self.accept(raw).status_code, 400)
        _, raw = self.owner_invite()
        invitation = EnterpriseInvitation.objects.get(token_hash=token_digest(raw))
        revoke = self.call(
            EnterpriseInvitationRevokeView, token=self.root_token, invitation_id=invitation.pk,
        )
        self.assertEqual(revoke.status_code, 200)
        self.assertEqual(self.accept(raw).status_code, 400)
        with patch("apps.api.v1.users.enterprise_views.send_mail", return_value=0):
            failed = self.call(SuperadminEnterpriseInvitesView, token=self.root_token, data={
                "email": "fail-e53@example.test", "company_name": "Fail", "sector": "Test",
            })
        self.assertEqual(failed.status_code, 503)
        self.assertFalse(EnterpriseInvitation.objects.filter(email="fail-e53@example.test").exists())

    def test_new_accounts_without_invitation_remain_unverified_and_cannot_login(self):
        legacy = User.objects.create_user(
            username="old_enterprise", email="old-e53@example.test",
            password="E53-Complex-Account!", role="enterprise", is_active=True,
        )
        Enterprise.objects.create(user=legacy, company_name="Legacy", sector="X")
        self.assertEqual(
            self.call(EstablishmentWebLoginView, data={
                "email": legacy.email, "password": "E53-Complex-Account!",
            }).status_code, 403,
        )
        self.assertEqual(
            self.call(LoginView, data={"email": legacy.email, "password": "E53-Complex-Account!"}).status_code, 403,
        )
        old = Token.objects.create(user=legacy)
        self.assertEqual(self.call(MeView, method="get", token=old.key, scheme="Token").status_code, 401)

    def test_owner_invites_recruiter_and_recruiter_cannot_invite_others(self):
        owner = self.make_owner()
        token = self.login_and_mfa(owner.email)
        sent = self.call(EnterpriseRecruiterInvitesView, token=token, data={
            "email": "recruiter-e53@example.test",
        })
        self.assertEqual(sent.status_code, 200)
        raw = re.search(r"#invitation=([A-Za-z0-9_-]+)", mail.outbox[-1].body).group(1)
        self.assertEqual(self.accept(raw).status_code, 200)
        recruiter = User.objects.get(email="recruiter-e53@example.test")
        self.assertEqual(recruiter.role, "enterprise")
        self.assertEqual(recruiter.enterprise_membership.enterprise, owner.enterprise_profile)
        self.assertFalse(hasattr(recruiter, "enterprise_profile"))
        recruiter_token = self.login_and_mfa(recruiter.email)
        dashboard = self.call(EnterpriseDashboardView, token=recruiter_token, method="get")
        self.assertEqual(dashboard.data["data"]["membership"], "recruiter")
        denied = self.call(EnterpriseRecruiterInvitesView, token=recruiter_token, data={
            "email": "intruder@example.test",
        })
        self.assertEqual(denied.status_code, 403)
        return_token = self.call(SuperadminEnterpriseInvitesView, token=recruiter_token, method="get")
        self.assertEqual(return_token.status_code, 403)

    def test_recruiter_revocation_terminates_all_its_web_sessions(self):
        owner = self.make_owner()
        token = self.login_and_mfa(owner.email)
        self.call(EnterpriseRecruiterInvitesView, token=token, data={"email": "staff@example.test"})
        raw = re.search(r"#invitation=([A-Za-z0-9_-]+)", mail.outbox[-1].body).group(1)
        self.assertEqual(self.accept(raw).status_code, 200)
        staff = User.objects.get(email="staff@example.test")
        staff_token = self.login_and_mfa(staff.email)
        member = staff.enterprise_membership
        response = self.call(EnterpriseRecruiterRevokeView, token=token, member_id=member.pk)
        self.assertEqual(response.status_code, 200)
        member.refresh_from_db()
        self.assertFalse(member.is_active)
        self.assertEqual(self.call(EnterpriseDashboardView, token=staff_token, method="get").status_code, 401)

    def test_invitation_and_recruiter_access_are_tenant_scoped(self):
        owner_a = self.make_owner()
        token_a = self.login_and_mfa(owner_a.email)
        owner_b = self.make_owner(email="another-owner@example.test", company="Autre Entreprise")
        token_b = self.login_and_mfa(owner_b.email)
        self.call(EnterpriseRecruiterInvitesView, token=token_a, data={"email": "staff-x@example.test"})
        invite = EnterpriseInvitation.objects.get(email="staff-x@example.test")
        forbidden = self.call(EnterpriseInvitationRevokeView, token=token_b, invitation_id=invite.pk)
        self.assertEqual(forbidden.status_code, 404)
        self.assertEqual(self.call(EnterpriseRecruitersView, token=token_b, method="get").data["data"], [])
        self.assertEqual(self.call(EnterpriseInvitationRevokeView, token=token_a, invitation_id=invite.pk).status_code, 200)

    def test_offers_and_applicants_are_filtered_by_company_and_author(self):
        owner_a = self.make_owner()
        token_a = self.login_and_mfa(owner_a.email)
        owner_b = self.make_owner(email="other-e53@example.test", company="Compagnie B")
        token_b = self.login_and_mfa(owner_b.email)
        published_a = Post.objects.create(author=owner_a, title="Offre A", post_type="opportunity")
        published_b = Post.objects.create(author=owner_b, title="Offre B", post_type="opportunity")
        forged = Post.objects.create(author=owner_b, title="Fausse offre A", post_type="opportunity")
        offer_a = Opportunity.objects.create(post=published_a, enterprise=owner_a.enterprise_profile)
        offer_b = Opportunity.objects.create(post=published_b, enterprise=owner_b.enterprise_profile)
        Opportunity.objects.create(post=forged, enterprise=owner_a.enterprise_profile)
        Application.objects.create(user=self.student, opportunity=offer_a)
        Application.objects.create(user=owner_b, opportunity=offer_b)
        dashboard = self.call(EnterpriseDashboardView, token=token_a, method="get")
        self.assertEqual(dashboard.data["data"]["stats"], {"opportunities": 1, "applications": 1})
        listing = self.call(EnterpriseOpportunitiesView, token=token_a, method="get")
        self.assertEqual([x["title"] for x in listing.data["data"]], ["Offre A"])
        cross = self.call(EnterpriseOfferApplicationsView, token=token_a, method="get", offer_id=offer_b.pk)
        self.assertEqual(cross.status_code, 404)
        mine = self.call(EnterpriseOfferApplicationsView, token=token_a, method="get", offer_id=offer_a.pk)
        self.assertEqual(mine.status_code, 200)
        self.assertEqual(mine.data["data"][0]["status"], "submitted")
        self.assertEqual(self.call(EnterpriseDashboardView, token=token_b, method="get").data["data"]["stats"]["opportunities"], 1)

    def test_invalid_tokens_and_anonymous_access_fail(self):
        self.assertEqual(self.call(EnterpriseInvitationPreviewView, data={"invitation": "missing"}).status_code, 400)
        self.assertEqual(self.call(EnterpriseDashboardView, method="get").status_code, 401)
        self.assertEqual(self.call(EnterpriseRecruiterInvitesView, data={"email": "x@y.test"}).status_code, 401)
        self.assertEqual(self.call(EnterpriseRecruiterRevokeView, member_id=999).status_code, 401)
