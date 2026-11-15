# backoffice/urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminAuditLogView, AdminStatsView, EnterpriseDashboardView, AdminUserViewSet, ImportJobListView, ImportView, ReportViewSet,
)

from .institution_directory_e31 import SuperadminInstitutionDirectoryE31
from .enterprise_directory_e32 import SuperadminEnterpriseDirectoryE32
from .user_directory_e34 import SuperadminUserDirectoryE34
from .user_security_e35 import SuperadminUserSecurityE35
from apps.api.v1.subscriptions.invoice_views import (
    InvoiceIssuerSettingsE38, InvoiceListE38, InvoiceIssueE38, InvoiceAdminPdfE38,
)
from .finance_register_e36 import SuperadminFinanceRegisterE36
from .content_directory_e57 import SuperadminContentDirectoryE57
from .statistics_portal_e60 import SuperadminStatisticsE60
from .audit_portal_e61 import SuperadminAuditDirectoryE61
from .security_portal_e62 import SuperadminSecurityDirectoryE62, SuperadminRevokeOwnSessionE62
from .moderation_portal_e59 import (
    SuperadminModerationDirectoryE59, SuperadminModerationDecisionE59,
)
from .import_portal_e58 import (
    SuperadminImportDirectoryE58, SuperadminImportPreviewE58, SuperadminImportExecuteE58,
)

from .enterprise_management_e24 import (
    EnterpriseOffersView, EnterpriseOfferDetailView, EnterpriseApplicationsView,
    EnterpriseApplicationDetailView, EnterprisePublicationsView,
)

router = DefaultRouter()
router.register(r"reports", ReportViewSet, basename="report")
router.register(r"users", AdminUserViewSet, basename="admin-user")

urlpatterns = [
    path("institutions/", SuperadminInstitutionDirectoryE31.as_view(), name="superadmin-institutions-e31"),
    path("enterprises/", SuperadminEnterpriseDirectoryE32.as_view(), name="superadmin-enterprises-e32"),
    path("user-directory/", SuperadminUserDirectoryE34.as_view(), name="superadmin-user-directory-e34"),
    path("user-directory/<int:pk>/security/", SuperadminUserSecurityE35.as_view(), name="superadmin-user-security-e35"),
    path("finance/register/", SuperadminFinanceRegisterE36.as_view(), name="superadmin-finance-register-e36"),
    path("content-directory/", SuperadminContentDirectoryE57.as_view(), name="superadmin-content-directory-e57"),
    path("statistics-v2/", SuperadminStatisticsE60.as_view(), name="superadmin-statistics-e60"),
    path("audit-v2/", SuperadminAuditDirectoryE61.as_view(), name="superadmin-audit-directory-e61"),
    path("security-v2/", SuperadminSecurityDirectoryE62.as_view(), name="superadmin-security-directory-e62"),
    path("security-v2/my-sessions/<int:session_id>/revoke/", SuperadminRevokeOwnSessionE62.as_view(), name="superadmin-security-revoke-session-e62"),
    path("moderation-v2/", SuperadminModerationDirectoryE59.as_view(), name="superadmin-moderation-directory-e59"),
    path("moderation-v2/<int:pk>/decision/", SuperadminModerationDecisionE59.as_view(), name="superadmin-moderation-decision-e59"),
    path("imports-v2/", SuperadminImportDirectoryE58.as_view(), name="superadmin-import-history-e58"),
    path("imports-v2/preview/", SuperadminImportPreviewE58.as_view(), name="superadmin-import-preview-e58"),
    path("imports-v2/execute/", SuperadminImportExecuteE58.as_view(), name="superadmin-import-execute-e58"),
    path("finance/issuer/", InvoiceIssuerSettingsE38.as_view(), name="e38-issuer"),
    path("finance/invoices/", InvoiceListE38.as_view(), name="e38-invoices"),
    path("finance/invoices/issue/", InvoiceIssueE38.as_view(), name="e38-invoice-issue"),
    path("finance/invoices/<int:invoice_id>/pdf/", InvoiceAdminPdfE38.as_view(), name="e38-invoice-pdf"),
    path("audit-log/", AdminAuditLogView.as_view(), name="admin-audit-log"),
    path("imports/", ImportJobListView.as_view(), name="import-jobs"),
    path("imports/upload/", ImportView.as_view(), name="import-upload"),
    path("stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("enterprise-dashboard/", EnterpriseDashboardView.as_view(), name="enterprise-dashboard"),
    path("enterprise/offers/", EnterpriseOffersView.as_view(), name="enterprise-offers-e24"),
    path("enterprise/offers/<int:offer_id>/", EnterpriseOfferDetailView.as_view(), name="enterprise-offer-e24"),
    path("enterprise/applications/", EnterpriseApplicationsView.as_view(), name="enterprise-applications-e24"),
    path("enterprise/applications/<int:application_id>/", EnterpriseApplicationDetailView.as_view(), name="enterprise-application-e24"),
    path("enterprise/publications/", EnterprisePublicationsView.as_view(), name="enterprise-publications-e24"),
]

urlpatterns += router.urls
