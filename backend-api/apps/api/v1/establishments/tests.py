"""Regression tests for write isolation of institution resources.

These are intentionally database-free checks of the DRF permission object and
viewset action selection. End-to-end API tests with actual users/institutions
must be added once the shared backend's dependency baseline is reproducible.
"""
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.api.v1.users.models import InstitutionAdmin, User, Student
from apps.api.v1.backoffice.views import AdminStatsView

from .models import Institution, Promotion, PromotionMembership, StudentInstitution, StudentAccountOrder
from .permissions import IsInstitutionManager, IsInstitutionScopedManager
from .views import InstitutionViewSet, PromotionViewSet, PromotionMembershipViewSet, PromotionJoinRequestViewSet, StudentAccountOrderViewSet


class InstitutionWritePermissionTests(SimpleTestCase):
    def setUp(self):
        self.permission = IsInstitutionManager()
        self.institution = SimpleNamespace(pk=18)

    def request_for(self, *, role="student", institution_id=None,
                    authenticated=True, superuser=False):
        user = SimpleNamespace(
            role=role,
            is_authenticated=authenticated,
            is_superuser=superuser,
        )
        if institution_id is not None:
            user.institution_admin_profile = SimpleNamespace(
                institution_id=institution_id, institution=SimpleNamespace(is_active=True),
            )
        return SimpleNamespace(user=user)

    def test_anonymous_cannot_write(self):
        request = self.request_for(authenticated=False)
        self.assertFalse(self.permission.has_permission(request, None))
        self.assertFalse(self.permission.has_object_permission(request, None, self.institution))

    def test_student_and_unrelated_admin_cannot_edit(self):
        for request in (
            self.request_for(role="student"),
            self.request_for(role="etablissement", institution_id=99),
        ):
            with self.subTest(role=request.user.role):
                self.assertFalse(self.permission.has_object_permission(request, None, self.institution))

    def test_institution_admin_can_edit_only_own_institution(self):
        request = self.request_for(role="etablissement", institution_id=18)
        self.assertTrue(self.permission.has_object_permission(request, None, self.institution))
        self.assertFalse(self.permission.has_object_permission(
            request, None, SimpleNamespace(pk=99),
        ))

    def test_platform_superadmins_can_edit(self):
        request = self.request_for(role="superAdmin")
        self.assertTrue(self.permission.has_object_permission(request, None, self.institution))

    def test_superuser_flag_without_platform_role_cannot_edit(self):
        request = self.request_for(role="student", superuser=True)
        self.assertFalse(self.permission.has_object_permission(request, None, self.institution))

    def test_viewset_requires_object_permission_for_all_default_write_actions(self):
        view = InstitutionViewSet()
        for action in ("update", "partial_update", "destroy"):
            with self.subTest(action=action):
                view.action = action
                permissions = view.get_permissions()
                self.assertTrue(any(isinstance(p, IsAuthenticated) for p in permissions))
                self.assertTrue(any(isinstance(p, IsInstitutionManager) for p in permissions))

    def test_public_reads_and_existing_membership_actions_stay_available(self):
        view = InstitutionViewSet()
        for action in ("list", "retrieve"):
            view.action = action
            self.assertTrue(any(isinstance(p, AllowAny) for p in view.get_permissions()))
        for action in ("join", "leave", "toggle_active", "images"):
            view.action = action
            self.assertFalse(any(
                isinstance(p, IsInstitutionManager) for p in view.get_permissions()
            ))

    def test_student_with_unexpected_admin_profile_still_cannot_edit(self):
        request = self.request_for(role="student", institution_id=18)
        self.assertFalse(self.permission.has_object_permission(request, None, self.institution))

    def test_only_superadmin_can_create_institution_permission(self):
        from apps.api.v1.core.permissions import IsSuperAdmin
        view = InstitutionViewSet()
        view.action = "create"
        self.assertTrue(any(isinstance(p, IsSuperAdmin) for p in view.get_permissions()))

    def test_inactive_institution_cannot_be_managed(self):
        request = self.request_for(role="etablissement", institution_id=18)
        request.user.institution_admin_profile.institution.is_active = False
        self.assertFalse(self.permission.has_object_permission(request, None, self.institution))
        self.assertFalse(IsInstitutionScopedManager().has_permission(request, None))

    def test_scoped_manager_permission(self):
        permission = IsInstitutionScopedManager()
        own = SimpleNamespace(institution_id=18)
        foreign = SimpleNamespace(institution_id=19)
        admin = self.request_for(role="etablissement", institution_id=18)
        student = self.request_for(role="student", institution_id=18)
        self.assertTrue(permission.has_permission(admin, None))
        self.assertTrue(permission.has_object_permission(admin, None, own))
        self.assertFalse(permission.has_object_permission(admin, None, foreign))
        self.assertFalse(permission.has_permission(student, None))


class InstitutionWriteHttpTests(TestCase):
    """Real DRF requests and database-backed institution ownership checks.

    Django TestCase uses a separate disposable test database; these tests do
    not operate on the development database or its existing records.
    """

    @classmethod
    def setUpTestData(cls):
        cls.institution_a = Institution.objects.create(
            name="Institution API A", acronym="APIA",
        )
        cls.institution_b = Institution.objects.create(
            name="Institution API B", acronym="APIB",
        )

        cls.admin_a = User.objects.create_user(
            username="api_admin_a",
            email="api-admin-a@example.test",
            password="test-password-a",
            role="etablissement",
            is_active=True,
        )
        cls.admin_b = User.objects.create_user(
            username="api_admin_b",
            email="api-admin-b@example.test",
            password="test-password-b",
            role="etablissement",
            is_active=True,
        )
        cls.student = User.objects.create_user(
            username="api_student",
            email="api-student@example.test",
            password="test-password-c",
            role="student",
            is_active=True,
        )
        cls.platform_admin = User.objects.create_user(
            username="api_superadmin",
            email="api-superadmin@example.test",
            password="test-password-d",
            role="superAdmin",
            is_active=True,
        )
        InstitutionAdmin.objects.create(
            user=cls.admin_a, institution=cls.institution_a,
        )
        InstitutionAdmin.objects.create(
            user=cls.admin_b, institution=cls.institution_b,
        )

    def call_institution(self, method, *, user=None, institution=None, data=None):
        institution = institution or self.institution_a
        factory = APIRequestFactory()
        url = f"/api/v1/establishments/institutions/{institution.pk}/"
        request = getattr(factory, method)(url, data=data or {}, format="json")
        if user is not None:
            force_authenticate(request, user=user)
        action = {"patch": "partial_update", "delete": "destroy"}[method]
        view = InstitutionViewSet.as_view({method: action})
        return view(request, pk=institution.pk)

    def test_anonymous_cannot_patch(self):
        response = self.call_institution(
            "patch", data={"name": "Unauthorized change"},
        )
        self.assertIn(response.status_code, (401, 403))
        self.institution_a.refresh_from_db()
        self.assertEqual(self.institution_a.name, "Institution API A")

    def test_student_cannot_patch_institution(self):
        response = self.call_institution(
            "patch", user=self.student, data={"name": "Student change"},
        )
        self.assertEqual(response.status_code, 403)
        self.institution_a.refresh_from_db()
        self.assertEqual(self.institution_a.name, "Institution API A")

    def test_unrelated_institution_admin_cannot_patch_or_delete(self):
        for method in ("patch", "delete"):
            with self.subTest(method=method):
                response = self.call_institution(
                    method, user=self.admin_b,
                    data={"name": "Foreign admin change"},
                )
                self.assertEqual(response.status_code, 403)
                self.assertTrue(
                    Institution.objects.filter(pk=self.institution_a.pk).exists()
                )
                self.institution_a.refresh_from_db()
                self.assertEqual(self.institution_a.name, "Institution API A")

    def test_own_institution_admin_can_patch(self):
        response = self.call_institution(
            "patch", user=self.admin_a, data={"name": "Institution A updated"},
        )
        self.assertEqual(response.status_code, 200)
        self.institution_a.refresh_from_db()
        self.assertEqual(self.institution_a.name, "Institution A updated")

    def test_platform_superadmin_can_patch(self):
        response = self.call_institution(
            "patch", user=self.platform_admin,
            data={"description": "Platform-approved update"},
        )
        self.assertEqual(response.status_code, 200)
        self.institution_a.refresh_from_db()
        self.assertEqual(
            self.institution_a.description, "Platform-approved update"
        )

    def test_only_platform_superadmin_can_create_institution(self):
        def create_as(user):
            factory = APIRequestFactory()
            request = factory.post(
                "/api/v1/establishments/institutions/",
                {"name": "New School", "acronym": "NEW"}, format="json",
            )
            if user is not None:
                force_authenticate(request, user=user)
            return InstitutionViewSet.as_view({"post": "create"})(request)

        before = Institution.objects.count()
        for user in (None, self.student, self.admin_a, self.admin_b):
            with self.subTest(user=getattr(user, "role", "anonymous")):
                response = create_as(user)
                self.assertIn(response.status_code, (401, 403))
                self.assertEqual(Institution.objects.count(), before)
        response = create_as(self.platform_admin)
        self.assertEqual(response.status_code, 201, getattr(response, "data", None))
        self.assertEqual(Institution.objects.count(), before + 1)

    def _request(self, view_class, method, url, *, action, user=None, data=None, pk=None):
        factory = APIRequestFactory()
        request = getattr(factory, method)(url, data=data or {}, format="json")
        if user is not None:
            force_authenticate(request, user=user)
        view = view_class.as_view({method: action})
        return view(request, **({"pk": pk} if pk is not None else {}))

    def test_promotion_creation_scoped_to_owned_institution(self):
        url = "/api/v1/establishments/promotions/"
        payload = {"institution": self.institution_a.pk, "name": "L1 Info"}
        for user in (self.student, self.admin_b):
            with self.subTest(role=user.role, id=user.pk):
                response = self._request(
                    PromotionViewSet, "post", url, action="create", user=user, data=payload,
                )
                self.assertIn(response.status_code, (400, 403))
                self.assertFalse(Promotion.objects.filter(
                    institution=self.institution_a, name="L1 Info",
                ).exists())
        response = self._request(
            PromotionViewSet, "post", url, action="create", user=self.admin_a, data=payload,
        )
        self.assertEqual(response.status_code, 201, getattr(response, "data", None))

    def test_promotion_mutation_denied_for_other_institution(self):
        promo = Promotion.objects.create(
            institution=self.institution_a, name="Class A", is_general=False,
        )
        url = f"/api/v1/establishments/promotions/{promo.pk}/"
        response = self._request(
            PromotionViewSet, "patch", url, action="partial_update",
            user=self.admin_b, pk=promo.pk, data={"name": "Leaked"},
        )
        self.assertIn(response.status_code, (403, 404))
        promo.refresh_from_db()
        self.assertEqual(promo.name, "Class A")
        response = self._request(
            PromotionViewSet, "patch", url, action="partial_update",
            user=self.admin_a, pk=promo.pk, data={"name": "Updated by A"},
        )
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))

    def test_membership_change_and_delegate_stay_in_institution(self):
        from datetime import date
        student_profile = Student.objects.create(
            user=self.student, gender="M", date_of_birth=date(2002, 1, 2),
            student_id="E3-STUDENT-1",
        )
        StudentInstitution.objects.create(
            student=student_profile, institution=self.institution_a,
        )
        member = PromotionMembership.objects.get(
            student=student_profile,
            promotion=self.institution_a.general_promotion,
        )
        url = f"/api/v1/establishments/memberships/{member.pk}/make_delegate/"
        foreign = self._request(
            PromotionMembershipViewSet, "post", url, action="make_delegate",
            user=self.admin_b, pk=member.pk,
        )
        self.assertIn(foreign.status_code, (403, 404))
        member.refresh_from_db()
        self.assertFalse(member.is_delegate)

        allowed = self._request(
            PromotionMembershipViewSet, "post", url, action="make_delegate",
            user=self.admin_a, pk=member.pk,
        )
        self.assertEqual(allowed.status_code, 200, getattr(allowed, "data", None))

        edit_url = f"/api/v1/establishments/memberships/{member.pk}/"
        moved = self._request(
            PromotionMembershipViewSet, "patch", edit_url, action="partial_update",
            user=self.admin_a, pk=member.pk,
            data={"promotion": self.institution_b.general_promotion.pk},
        )
        self.assertEqual(moved.status_code, 200, getattr(moved, "data", None))
        member.refresh_from_db()
        self.assertEqual(member.promotion.institution_id, self.institution_a.pk)

    def test_direct_membership_creation_not_supported(self):
        response = self._request(
            PromotionMembershipViewSet, "post", "/api/v1/establishments/memberships/",
            action="create", user=self.admin_a,
            data={"promotion": self.institution_a.general_promotion.pk},
        )
        self.assertEqual(response.status_code, 405)

    def test_join_requests_cannot_be_arbitrarily_rewritten(self):
        self.assertFalse(hasattr(PromotionJoinRequestViewSet, "partial_update"))
        self.assertFalse(hasattr(PromotionJoinRequestViewSet, "destroy"))

    def test_order_cannot_self_approve_or_target_other_school(self):
        url = "/api/v1/establishments/account-orders/"
        data = {
            "institution": self.institution_a.pk, "year": 2026, "quantity": 5,
            "status": "approved", "price_per_account": "0.00",
        }
        student_response = self._request(
            StudentAccountOrderViewSet, "post", url,
            action="create", user=self.student, data=data,
        )
        self.assertEqual(student_response.status_code, 403)
        other_school = self._request(
            StudentAccountOrderViewSet, "post", url,
            action="create", user=self.admin_b, data=data,
        )
        self.assertEqual(other_school.status_code, 403)
        own = self._request(
            StudentAccountOrderViewSet, "post", url,
            action="create", user=self.admin_a, data=data,
        )
        self.assertEqual(own.status_code, 201, getattr(own, "data", None))
        order = StudentAccountOrder.objects.get(institution=self.institution_a)
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.price_per_account, 0)

        detail_url = f"{url}{order.pk}/"
        school_approval = self._request(
            StudentAccountOrderViewSet, "patch", detail_url,
            action="partial_update", user=self.admin_a, pk=order.pk,
            data={"status": "approved"},
        )
        self.assertEqual(school_approval.status_code, 403)
        platform_approval = self._request(
            StudentAccountOrderViewSet, "patch", detail_url,
            action="partial_update", user=self.platform_admin, pk=order.pk,
            data={"status": "approved", "price_per_account": "200.00"},
        )
        self.assertEqual(platform_approval.status_code, 200, getattr(platform_approval, "data", None))
        order.refresh_from_db()
        self.assertEqual(order.status, "approved")

    def test_backoffice_stats_only_expose_own_school(self):
        def stats_for(user):
            factory = APIRequestFactory()
            request = factory.get("/api/v1/backoffice/stats/")
            force_authenticate(request, user=user)
            return AdminStatsView.as_view()(request)

        forbidden = stats_for(self.student)
        self.assertEqual(forbidden.status_code, 403)
        for user, own_school in ((self.admin_a, self.institution_a), (self.admin_b, self.institution_b)):
            response = stats_for(user)
            self.assertEqual(response.status_code, 200, getattr(response, "data", None))
            self.assertEqual(response.data["data"]["scope"], "institution")
            self.assertEqual(response.data["data"]["institution_name"], own_school.name)
            self.assertEqual(response.data["data"]["users"]["institution_admins"], 1)

