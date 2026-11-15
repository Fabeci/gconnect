"""E58: no silent account creation; protected preview and atomic catalogue imports."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory

from apps.api.v1.backoffice.models import ImportJob
from apps.api.v1.establishments.models import Institution, Promotion
from apps.api.v1.users.models import (
    EstablishmentWebSession, PrivilegedMFADevice, User,
)
from apps.api.v1.users.privileged_security import encrypt_totp, generate_totp_secret
from django.utils import timezone


class SuperadminImportE58Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(
            username="e58admin", email="e58admin@example.test",
            password="Strong-E58-Password!", role="superAdmin", is_active=True,
        )
        cls.enterprise = User.objects.create_user(
            username="e58enterprise", email="e58company@example.test",
            password="Strong-E58-Password!", role="enterprise", is_active=True,
        )
        PrivilegedMFADevice.objects.create(
            user=cls.admin, encrypted_secret=encrypt_totp(generate_totp_secret()),
            confirmed_at=timezone.now(),
        )
        cls.institution = Institution.objects.create(
            name="Campus Test E58", text_code="CAMPUS-E58", is_active=True,
        )

    def setUp(self):
        request=APIRequestFactory().get("/")
        _, token=EstablishmentWebSession.issue(self.admin, request)
        self.admin_client=APIClient()
        self.admin_client.credentials(HTTP_AUTHORIZATION="WebToken "+token)
        self.guest=APIClient()
        self.student=APIClient()

    @staticmethod
    def file(data, name="promotions.csv"):
        return SimpleUploadedFile(name, data.encode("utf-8"), content_type="text/csv")

    def preview(self, data, kind="promotions", institution=None):
        payload={"import_type":kind,"file":self.file(data, "import.csv")}
        if institution is not None:
            payload["institution"]=str(institution)
        return self.admin_client.post("/api/v1/backoffice/imports-v2/preview/", payload, format="multipart")

    def execute(self, data, token, kind="promotions", institution=None, confirmation="CONFIRMER"):
        payload={
            "import_type":kind,"file":self.file(data,"import.csv"),
            "preview_token":token,"confirmation":confirmation,
        }
        if institution is not None:
            payload["institution"]=str(institution)
        return self.admin_client.post("/api/v1/backoffice/imports-v2/execute/", payload, format="multipart")

    def test_read_only_history_is_restricted_and_hides_legacy_generated_passwords(self):
        ImportJob.objects.create(
            import_type="students", file_name="old.csv", total_rows=2,
            success_count=1, error_count=1,
            created_rows=[{"generated_password":"NEVER-LEAK-THIS-SECRET"}],
        )
        self.assertEqual(self.guest.get("/api/v1/backoffice/imports-v2/").status_code,401)
        body=self.admin_client.get("/api/v1/backoffice/imports-v2/")
        self.assertEqual(body.status_code,200,body.data)
        self.assertEqual(body.data["data"]["summary"]["imports"],1)
        self.assertEqual(body.data["data"]["summary"]["anomalies"],1)
        self.assertNotIn("NEVER-LEAK",str(body.data))
        self.assertNotIn("created_rows",str(body.data))
        self.assertEqual(body["Cache-Control"],"no-store")

    def test_preview_is_non_mutating_and_commit_requires_same_file_and_confirmation(self):
        rows="name,year,department,level\nPromotion 2026,2026,Informatique,MASTER\n"
        before=Promotion.objects.count()
        pre=self.preview(rows,institution=self.institution.pk)
        self.assertEqual(pre.status_code,200,pre.data)
        data=pre.data["data"]
        self.assertTrue(data["executable"])
        self.assertEqual(data["rows"],1)
        self.assertIsNotNone(data["preview_token"])
        self.assertEqual(Promotion.objects.count(),before)
        self.assertEqual(
            self.execute(rows,data["preview_token"],institution=self.institution.pk,confirmation="non").status_code,400,
        )
        changed=rows.replace("Promotion 2026","Promotion falsifiée")
        self.assertEqual(
            self.execute(changed,data["preview_token"],institution=self.institution.pk).status_code,400,
        )
        self.assertEqual(Promotion.objects.count(),before)
        result=self.execute(rows,data["preview_token"],institution=self.institution.pk)
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(Promotion.objects.count(),before+1)
        self.assertEqual(result.data["data"]["integrated"],1)
        job=ImportJob.objects.get(id=result.data["data"]["job_id"])
        self.assertEqual(job.created_rows,[])
        self.assertEqual(job.errors,[])
        self.assertEqual(job.success_count,1)
        self.assertEqual(self.execute(rows,data["preview_token"],institution=self.institution.pk).status_code,409)

    def test_establishment_import_with_anomalies_does_not_write_any_rows(self):
        before=Institution.objects.count()
        rows="name,text_code\nNew School,E58-ALPHA\nNew School,E58-BETA\n"
        pre=self.preview(rows,kind="establishments")
        self.assertEqual(pre.status_code,200)
        self.assertFalse(pre.data["data"]["executable"])
        self.assertTrue(pre.data["data"]["errors"])
        self.assertEqual(Institution.objects.count(),before)

    def test_student_and_alumni_are_preview_only_not_auto_created(self):
        for kind in ["students","alumni"]:
            rows="email,username\nnew@example.test,student58\n"
            pre=self.preview(rows,kind=kind,institution=self.institution.pk)
            self.assertEqual(pre.status_code,200,pre.data)
            self.assertFalse(pre.data["data"]["executable"])
            self.assertIsNone(pre.data["data"]["preview_token"])
            attempted=self.execute(rows,"invalid",kind=kind,institution=self.institution.pk)
            self.assertEqual(attempted.status_code,403)
        self.assertFalse(User.objects.filter(email="new@example.test").exists())

    def test_invalid_file_and_pagination_cannot_write(self):
        response=self.admin_client.get("/api/v1/backoffice/imports-v2/?page=-1")
        self.assertEqual(response.status_code,400)
        bad=self.admin_client.post("/api/v1/backoffice/imports-v2/preview/",{
            "import_type":"establishments",
            "file":SimpleUploadedFile("bad.csv",b"name,name\nA,B\n",content_type="text/csv"),
        },format="multipart")
        self.assertEqual(bad.status_code,400)
        oversize=self.admin_client.post("/api/v1/backoffice/imports-v2/preview/",{
            "import_type":"establishments",
            "file":SimpleUploadedFile("bad.csv",b"name\n"+b"X"*2100000,content_type="text/csv"),
        },format="multipart")
        self.assertEqual(oversize.status_code,400)
