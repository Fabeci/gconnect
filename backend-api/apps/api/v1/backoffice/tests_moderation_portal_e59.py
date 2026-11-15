"""E59: secured case register and confirmed, audited moderation decisions."""
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from apps.api.v1.backoffice.models import Report
from apps.api.v1.core.models import AuditLogEntry
from apps.api.v1.posts.models import Comment, Post
from apps.api.v1.users.models import (
    Enterprise, EstablishmentWebSession, PrivilegedMFADevice, User,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret


class ModerationE59Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="e59admin", email="admin59@example.test",
            password="Complex-Admin-E59!", role="superAdmin", is_active=True,
        )
        cls.enterprise_user = User.objects.create_user(
            username="e59business", email="enterprise59@example.test",
            password="Complex-E59!", role="enterprise", is_active=True,
        )
        cls.reporter = User.objects.create_user(
            username="e59reporter", email="reporter59@example.test",
            password="Complex-E59!", role="student", is_active=True,
        )
        cls.target = User.objects.create_user(
            username="e59target", email="target59@example.test",
            password="Complex-E59!", role="student", is_active=True,
        )
        for user in (cls.admin, cls.enterprise_user):
            PrivilegedMFADevice.objects.create(
                user=user, encrypted_secret=encrypt_totp(generate_totp_secret()),
                confirmed_at=timezone.now(),
            )
        Enterprise.objects.create(
            user=cls.enterprise_user, company_name="Horizon E59", sector="IT",
            verified_at=timezone.now(),
        )
        cls.post = Post.objects.create(
            author=cls.target, title="Annonce test E59",
            content="Contenu à examiner", post_type=Post.PostType.DISCUSSION,
        )
        cls.comment = Comment.objects.create(
            user=cls.target, post=cls.post, content="Commentaire de test",
        )
        cls.pending = Report.objects.create(
            reporter=cls.reporter, post=cls.post,
            reason=Report.Reason.HARASSMENT, description="Signalement sérieux <img>",
        )
        cls.comment_case = Report.objects.create(
            reporter=cls.reporter, comment=cls.comment,
            reason=Report.Reason.SPAM, description="Spam répétitif",
        )
        cls.user_case = Report.objects.create(
            reporter=cls.reporter, reported_user=cls.target,
            reason=Report.Reason.FAKE_INFO, description="Fausse information",
        )
        cls.dismissed = Report.objects.create(
            reporter=cls.reporter, post=cls.post,
            reason=Report.Reason.INAPPROPRIATE,
            status=Report.Status.DISMISSED,
            reviewed_by=cls.admin,
            reviewed_at=timezone.now(),
        )

    def setUp(self):
        req = APIRequestFactory().get("/")
        _, admin_token = EstablishmentWebSession.issue(self.admin, req)
        _, enterprise_token = EstablishmentWebSession.issue(self.enterprise_user, req)
        self.admin_client = APIClient()
        self.admin_client.credentials(HTTP_AUTHORIZATION="WebToken " + admin_token)
        self.enterprise_client = APIClient()
        self.enterprise_client.credentials(HTTP_AUTHORIZATION="WebToken " + enterprise_token)
        self.guest = APIClient()
        self.list_url = reverse("superadmin-moderation-directory-e59")

    def decision(self, report_id, decision="dismiss", confirmation="CONFIRMER", reason=""):
        return self.admin_client.post(
            reverse("superadmin-moderation-decision-e59", args=[report_id]),
            {"decision": decision, "confirmation": confirmation, "reason": reason},
            format="json",
        )

    def test_privileged_session_and_role_mandatory_for_read_and_write(self):
        self.assertEqual(self.guest.get(self.list_url).status_code, 401)
        self.assertEqual(self.enterprise_client.get(self.list_url).status_code, 403)
        path = reverse("superadmin-moderation-decision-e59", args=[self.pending.pk])
        self.assertEqual(self.guest.post(path, {"decision": "dismiss"}, format="json").status_code, 401)
        self.assertEqual(self.enterprise_client.post(path, {
            "decision": "dismiss", "confirmation": "CONFIRMER",
        }, format="json").status_code, 403)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Report.Status.PENDING)

    def test_real_summary_search_filters_pagination_and_no_private_fields(self):
        resp = self.admin_client.get(self.list_url)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp["Cache-Control"], "no-store")
        data = resp.data["data"]
        self.assertEqual(data["summary"]["total"], 4)
        self.assertEqual(data["summary"]["pending"], 3)
        self.assertEqual(data["summary"]["resolved"], 1)
        self.assertEqual(data["summary"]["critical_pending"], 1)
        self.assertEqual(data["summary"]["reviewed_30d"], 1)
        self.assertEqual(data["by_reason"]["harassment"], 1)
        self.assertEqual(data["count"], 3)
        self.assertEqual(len(data["results"]), 3)
        incident = next(x for x in data["results"] if x["id"] == self.pending.pk)
        self.assertEqual(incident["target"], "post")
        self.assertEqual(incident["target_title"], "Annonce test E59")
        self.assertTrue(incident["can_hide"])
        self.assertIn("<img>", incident["description"])  # frontend escapes
        for field in ("email", "password", "token", "mfa", "resume"):
            self.assertNotIn(field, incident)
        self.assertEqual(self.admin_client.get(self.list_url, {"status": "all"}).data["data"]["count"], 4)
        self.assertEqual(self.admin_client.get(self.list_url, {"status": "dismissed"}).data["data"]["count"], 1)
        self.assertEqual(self.admin_client.get(self.list_url, {"target": "comment"}).data["data"]["count"], 1)
        self.assertEqual(self.admin_client.get(self.list_url, {"target": "user"}).data["data"]["count"], 1)
        self.assertEqual(self.admin_client.get(self.list_url, {"reason": "spam"}).data["data"]["count"], 1)
        self.assertEqual(self.admin_client.get(self.list_url, {"search": "Annonce"}).data["data"]["count"], 1)
        self.assertEqual(self.admin_client.get(self.list_url, {"page": 2, "page_size": 2}).data["data"]["count"], 3)

    def test_bad_query_is_rejected(self):
        for params in (
            {"status": "other"}, {"target": "file"}, {"reason": "hacker"},
            {"page": 0}, {"page": "a"}, {"page_size": 51},
        ):
            self.assertEqual(self.admin_client.get(self.list_url, params).status_code, 400, params)
        self.assertEqual(self.admin_client.get(self.list_url, {"page": 42}).status_code, 404)

    def test_dismiss_requires_explicit_confirmation_and_writes_audit(self):
        self.assertEqual(self.decision(self.pending.pk, confirmation="NON").status_code, 400)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Report.Status.PENDING)
        result = self.decision(self.pending.pk)
        self.assertEqual(result.status_code, 200, result.data)
        self.pending.refresh_from_db()
        self.post.refresh_from_db()
        self.assertEqual(self.pending.status, Report.Status.DISMISSED)
        self.assertEqual(self.pending.reviewed_by_id, self.admin.pk)
        self.assertFalse(self.post.is_hidden_by_admin)
        self.assertTrue(AuditLogEntry.objects.filter(
            action="report_reviewed", metadata__report_id=self.pending.pk,
        ).exists())
        self.assertEqual(self.decision(self.pending.pk).status_code, 409)

    def test_hide_requires_reason_not_empty_and_only_applies_to_post(self):
        self.assertEqual(self.decision(self.pending.pk, decision="hide_post", reason="court").status_code, 400)
        self.assertEqual(self.decision(self.comment_case.pk, decision="hide_post", reason="Motif valide pour masquer ce contenu").status_code, 400)
        self.assertEqual(self.decision(self.user_case.pk, decision="hide_post", reason="Motif valide pour masquer ce contenu").status_code, 400)
        self.post.refresh_from_db()
        self.assertFalse(self.post.is_hidden_by_admin)
        reason = "Contenu examiné et reconnu contraire aux règles de la communauté."
        result = self.decision(self.pending.pk, decision="hide_post", reason=reason)
        self.assertEqual(result.status_code, 200, result.data)
        self.post.refresh_from_db()
        self.pending.refresh_from_db()
        self.assertTrue(self.post.is_hidden_by_admin)
        self.assertEqual(self.post.hidden_reason, reason)
        self.assertEqual(self.pending.status, Report.Status.ACTIONED)
        self.assertTrue(AuditLogEntry.objects.filter(
            action="post_hidden", metadata__report_id=self.pending.pk,
        ).exists())
        self.assertTrue(AuditLogEntry.objects.filter(
            action="report_reviewed", metadata__report_id=self.pending.pk,
        ).exists())
        self.assertEqual(self.decision(self.pending.pk, decision="hide_post", reason=reason).status_code, 409)

    def test_unknown_actions_never_touch_reports(self):
        for decision in ("ban_user", "delete", "restore", "", "hide_comment"):
            self.assertEqual(self.decision(self.pending.pk, decision=decision).status_code, 400)
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, Report.Status.PENDING)
