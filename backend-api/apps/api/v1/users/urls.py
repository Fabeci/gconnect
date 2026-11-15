# urls.py
from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.api.v1.users.viewsets.alumni import AlumniViewSet
from apps.api.v1.users.viewsets.student import StudentViewSet
from .views import (
    CheckInstitutionCodeView, LoginView, LogoutView, MeView, StudentRegisterView,
    UserPublicProfileView, VerifyOTPView, ResendOTPView, ForgotPasswordView, ResetPasswordView,
    ProfilePrivacyView, ChangePasswordView,
    LoginSessionsView, DeleteAccountView, ExportPersonalDataView, SearchHistoryView,
    AlumniRegisterView, GoogleLoginView,
)

from .web_views import (
    EstablishmentWebLoginView, EstablishmentWebLogoutView,
    EstablishmentWebSessionsView, EstablishmentWebRevokeSessionView, EstablishmentWebResumeView,
)

from .privileged_views import (
    EstablishmentInvitationsView, EstablishmentInvitationRevokeView,
    EstablishmentInvitationPreviewView, EstablishmentInvitationAcceptView,
    PrivilegedMFASetupView, PrivilegedMFAVerifyView, PrivilegedEmailResendView,
)

from .enterprise_views import (
    SuperadminEnterpriseInvitesView, EnterpriseRecruiterInvitesView,
    EnterpriseInvitationRevokeView, EnterpriseInvitationPreviewView,
    EnterpriseInvitationAcceptView, EnterpriseDashboardView,
    EnterpriseRecruitersView, EnterpriseRecruiterRevokeView,
    EnterpriseOpportunitiesView, EnterpriseOfferApplicationsView,
)

router = DefaultRouter()
router.register(r'students', StudentViewSet, basename='students')
router.register(r'alumni', AlumniViewSet, basename='alumni')


from .professional_profile_views import ProfessionalProfileView
from .professional_password_views import ProfessionalPasswordChangeView

urlpatterns = [
    path('admin/enterprise-invitations/', SuperadminEnterpriseInvitesView.as_view(), name='admin-enterprise-invitations'),
    path('enterprise/invitations/', EnterpriseRecruiterInvitesView.as_view(), name='enterprise-recruiter-invitations'),
    path('enterprise/invitations/<int:invitation_id>/revoke/', EnterpriseInvitationRevokeView.as_view(), name='enterprise-invitation-revoke'),
    path('enterprise/invitations/preview/', EnterpriseInvitationPreviewView.as_view(), name='enterprise-invitation-preview'),
    path('enterprise/invitations/accept/', EnterpriseInvitationAcceptView.as_view(), name='enterprise-invitation-accept'),
    path('enterprise/dashboard/', EnterpriseDashboardView.as_view(), name='enterprise-dashboard-e53'),
    path('enterprise/recruiters/', EnterpriseRecruitersView.as_view(), name='enterprise-recruiters'),
    path('enterprise/recruiters/<int:member_id>/revoke/', EnterpriseRecruiterRevokeView.as_view(), name='enterprise-recruiter-revoke'),
    path('enterprise/offers/', EnterpriseOpportunitiesView.as_view(), name='enterprise-offers'),
    path('enterprise/offers/<int:offer_id>/applications/', EnterpriseOfferApplicationsView.as_view(), name='enterprise-offer-applications'),
    path('web-profile/', ProfessionalProfileView.as_view(), name='web-professional-profile'),
    path('web-change-password/', ProfessionalPasswordChangeView.as_view(), name='web-professional-password-change'),
    path('login/', LoginView.as_view(), name='login'),
    path('admin/invitations/', EstablishmentInvitationsView.as_view(), name='admin-invitations'),
    path('admin/invitations/<int:invitation_id>/revoke/', EstablishmentInvitationRevokeView.as_view(), name='admin-invitation-revoke'),
    path('invitations/preview/', EstablishmentInvitationPreviewView.as_view(), name='invitation-preview'),
    path('invitations/accept/', EstablishmentInvitationAcceptView.as_view(), name='invitation-accept'),
    path('web-mfa/setup/', PrivilegedMFASetupView.as_view(), name='web-mfa-setup'),
    path('web-mfa/verify/', PrivilegedMFAVerifyView.as_view(), name='web-mfa-verify'),
    path('web-mfa/email-resend/', PrivilegedEmailResendView.as_view(), name='web-mfa-email-resend'),
    path('web-login/', EstablishmentWebLoginView.as_view(), name='web-login'),
    path('web-resume/', EstablishmentWebResumeView.as_view(), name='web-resume'),
    path('web-logout/', EstablishmentWebLogoutView.as_view(), name='web-logout'),
    path('web-sessions/', EstablishmentWebSessionsView.as_view(), name='web-sessions'),
    path('web-sessions/<int:session_id>/revoke/', EstablishmentWebRevokeSessionView.as_view(), name='web-session-revoke'),
    path('google-login/', GoogleLoginView.as_view(), name='google-login'),
    path('register/student/check-code/', CheckInstitutionCodeView.as_view(), name='check-institution-code'),
    path('register/student/', StudentRegisterView.as_view(), name='student-register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('otp/resend/', ResendOTPView.as_view(), name='otp-resend'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('register/alumni/', AlumniRegisterView.as_view(), name='alumni-register'),
    path('me/', MeView.as_view(), name='me'),
    path('me/privacy/', ProfilePrivacyView.as_view(), name='profile-privacy'),
    path('me/change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('me/sessions/', LoginSessionsView.as_view(), name='login-sessions'),
    path('me/delete-account/', DeleteAccountView.as_view(), name='delete-account'),
    path('me/export-data/', ExportPersonalDataView.as_view(), name='export-personal-data'),
    path('me/search-history/', SearchHistoryView.as_view(), name='search-history'),
    path('<int:user_id>/', UserPublicProfileView.as_view(), name='user-public-profile'),
]

urlpatterns += router.urls
