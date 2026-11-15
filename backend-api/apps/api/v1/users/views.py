from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from django.db import transaction
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.authtoken.models import Token
from apps.api.v1.establishments.models import Institution, Promotion, PromotionMembership, StudentAccountOrder
from apps.api.v1.users.models import Student, User, ProfilePrivacy, LoginAttempt, LoginSession, SearchHistory, VerificationToken, EstablishmentWebSession
from apps.api.v1.users.serializers import ProfilePrivacySerializer
import logging
import random
from django.core.mail import send_mail
from django.conf import settings
from apps.api.v1.core.responses import success_response, error_response
from apps.api.v1.core.validators import validate_image_upload
from apps.api.v1.core.audit import log_audit_event
from apps.api.v1.establishments.models import AlumniInstitution, StudentInstitution
from apps.api.v1.subscriptions.quotas import lock_institution, require_available_school_seat
from apps.api.v1.core.sms_service import send_sms
from apps.api.v1.users.throttles import (
    LoginThrottle, OtpThrottle, OtpResendThrottle,
    ForgotPasswordThrottle, RegistrationThrottle,
)
import uuid
import urllib.request

logger = logging.getLogger(__name__)


class CheckInstitutionCodeView(APIView):
    permission_classes = []
    throttle_classes = [RegistrationThrottle]

    def post(self, request):
        input_code = request.data.get('code')

        if not input_code:
            return error_response("Code requis", status_code=400)

        try:
            if len(input_code) == 6 and input_code.isdigit():
                institution = Institution.objects.get(text_code=input_code)
            else:
                # On suppose que c'est un UUID (QR)
                institution = Institution.objects.get(qr_uuid=uuid.UUID(input_code))
        except (Institution.DoesNotExist, ValueError, TypeError):
            return error_response("Code ou QR invalide", status_code=400)

        session_token = str(uuid.uuid4())
        request.session[session_token] = {
            'institution_id': institution.id,
            'institution_name': institution.name
        }

        return success_response("Établissement reconnu", {
            "session_token": session_token,
            "institution_id": institution.id,
            "institution_name": institution.name
        })


def get_available_valid_order(institution):
    year = timezone.now().year
    orders = StudentAccountOrder.objects.filter(
        institution=institution,
        year=year,
        status='approved'
    ).order_by('created_at')

    for order in orders:
        if order.remaining > 0:
            return order
    return None


class StudentRegisterView(APIView):
    permission_classes = []
    throttle_classes = [RegistrationThrottle]

    def post(self, request):
        session_token = request.data.get("session_token")
        session_data = request.session.get(session_token)

        if not session_data:
            return error_response("Token invalide ou expiré", status_code=400)

        email = request.data.get("email")
        username = request.data.get("username")

        if User.objects.filter(email=email).exists():
            return error_response("Cet email est déjà utilisé.", status_code=400)

        if User.objects.filter(username=username).exists():
            return error_response("Ce nom d'utilisateur est déjà pris.", status_code=400)

        try:
            institution = Institution.objects.get(id=session_data['institution_id'])
        except Institution.DoesNotExist:
            return error_response("Établissement introuvable", status_code=400)

        order = get_available_valid_order(institution)
        if not order:
            return error_response("Aucune commande de comptes approuvée disponible pour cet établissement.", status_code=403)

        required_fields = ["password", "first_name", "last_name", "phone_number", "gender", "date_of_birth", "student_id"]
        missing = [f for f in required_fields if not request.data.get(f)]
        if missing:
            return error_response(f"Champs requis manquants : {', '.join(missing)}", status_code=400)

        password = request.data.get("password")
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_password(password)
        except DjangoValidationError as exc:
            return error_response(" ".join(exc.messages), status_code=400)

        # Création utilisateur inactif
        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            first_name=request.data.get("first_name"),
            last_name=request.data.get("last_name"),
            phone_number=request.data.get("phone_number", ""),
            role='student',
            is_active=False
        )

        student = Student.objects.create(
            user=user,
            gender=request.data.get("gender"),
            date_of_birth=request.data.get("date_of_birth"),
            student_id=request.data.get("student_id")
        )

        student.institutions.add(institution)
        try:
            general_promotion = Promotion.objects.get(institution=institution, is_general=True)
            membership, _ = PromotionMembership.objects.get_or_create(
                student=student,
                promotion=general_promotion,
                defaults={'is_approved': True},
            )
            if not membership.is_approved:
                membership.is_approved = True
                membership.save(update_fields=['is_approved'])
        except Promotion.DoesNotExist:
            pass

        request.session.pop(session_token, None)

        vtoken = VerificationToken.create_otp(user, VerificationToken.PURPOSE_EMAIL)

        send_mail(
            subject="Votre code de vérification GConnect",
            message=f"Bonjour {user.first_name},\n\nVoici votre code de vérification : {vtoken.token}\n\nCe code expire dans 15 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        try:
            order.increment_usage()
        except ValueError as e:
            return error_response(str(e), status_code=403)

        return success_response("Un code de vérification a été envoyé à votre email.", {
            "user_id": user.id,
            "email": user.email
        }, status_code=201)
    

class VerifyOTPView(APIView):
    permission_classes = []
    throttle_classes = [OtpThrottle]

    @transaction.atomic
    def post(self, request):
        user_id = request.data.get("user_id")
        otp = request.data.get("otp")

        if not user_id or not otp:
            return error_response("User ID et OTP sont requis.", status_code=400)

        try:
            user = User.objects.select_for_update().get(id=user_id)
        except User.DoesNotExist:
            return error_response("Utilisateur introuvable.", status_code=404)

        _, err = VerificationToken.verify(user, otp, VerificationToken.PURPOSE_EMAIL)
        if err:
            return error_response(err, status_code=400)

        if not user.is_active:
            institution_ids = set(StudentInstitution.objects.filter(
                student__user=user, seat_enabled=True,
            ).values_list('institution_id', flat=True))
            institution_ids.update(AlumniInstitution.objects.filter(
                alumni__user=user, seat_enabled=True,
            ).values_list('institution_id', flat=True))
            for institution_id in sorted(institution_ids):
                institution = lock_institution(institution_id)
                require_available_school_seat(institution)
            user.is_active = True
            user.save(update_fields=['is_active'])

        return success_response("Compte activé avec succès.")


class ResendOTPView(APIView):
    permission_classes = []
    throttle_classes = [OtpResendThrottle]

    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return error_response("User ID requis.", status_code=400)

        try:
            user = User.objects.get(id=user_id, is_active=False)
        except User.DoesNotExist:
            return error_response("Utilisateur introuvable ou déjà activé.", status_code=404)

        vtoken = VerificationToken.create_otp(user, VerificationToken.PURPOSE_EMAIL)

        send_mail(
            subject="Nouveau code de vérification GConnect",
            message=f"Bonjour {user.first_name},\n\nVoici votre nouveau code : {vtoken.token}\n\nCe code expire dans 15 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return success_response("Nouveau code envoyé.", {"user_id": user.id})


class ForgotPasswordView(APIView):
    permission_classes = []
    throttle_classes = [ForgotPasswordThrottle]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        if not email:
            return error_response("Email requis.", status_code=400)

        try:
            user = User.objects.get(email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # Réponse identique pour ne pas énumérer les emails
            return success_response("Si cet email existe, un code de réinitialisation a été envoyé.")

        vtoken = VerificationToken.create_otp(user, VerificationToken.PURPOSE_RESET, ttl_minutes=30)

        phone = (user.phone_number or '').strip()
        if not phone:
            return error_response(
                "Aucun numéro de téléphone associé à ce compte. Contactez le support.",
                status_code=400,
            )

        sms_body = (
            f"GConnect : votre code de réinitialisation est {vtoken.token}. "
            "Il expire dans 30 min."
        )
        ok = send_sms(to=phone, body=sms_body)
        if not ok:
            logger.error("forgot_password send_sms failed for user %s (phone %s)", user.id, phone)
            return error_response(
                "Impossible d'envoyer le SMS. Vérifiez la configuration Twilio.",
                status_code=503,
            )

        return success_response("Un code de réinitialisation a été envoyé par SMS.", {"user_id": user.id})


class ResetPasswordView(APIView):
    permission_classes = []
    throttle_classes = [OtpThrottle]

    def post(self, request):
        user_id = request.data.get("user_id")
        otp = request.data.get("otp")
        new_password = request.data.get("new_password")

        if not all([user_id, otp, new_password]):
            return error_response("user_id, otp et new_password sont requis.", status_code=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return error_response("Utilisateur introuvable.", status_code=404)

        _, err = VerificationToken.verify(user, otp, VerificationToken.PURPOSE_RESET)
        if err:
            return error_response(err, status_code=400)

        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return error_response(" ".join(exc.messages), status_code=400)

        user.set_password(new_password)
        user.save(update_fields=['password'])
        Token.objects.filter(user=user).delete()
        EstablishmentWebSession.objects.filter(user=user, revoked_at__isnull=True).update(
            revoked_at=timezone.now(),
        )
        log_audit_event("password_reset", user=user, request=request)
        return success_response("Mot de passe réinitialisé avec succès.")
    

LOGIN_LOCKOUT_THRESHOLD = 5
LOGIN_LOCKOUT_WINDOW_MINUTES = 15


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class LoginView(APIView):
    permission_classes = []
    throttle_classes = [LoginThrottle]

    def post(self, request):
        from datetime import timedelta
        from django.utils import timezone as dj_timezone

        email = request.data.get('email')
        password = request.data.get('password')
        ip_address = _client_ip(request)

        if not email or not password:
            return error_response("Email et mot de passe sont requis.")

        # Limitation des tentatives : au-delà de N échecs récents pour cet
        # email, on bloque temporairement — même si le mot de passe fourni
        # cette fois-ci est correct (protège contre un attaquant qui aurait
        # fini par trouver le bon mot de passe après une série d'essais).
        window_start = dj_timezone.now() - timedelta(minutes=LOGIN_LOCKOUT_WINDOW_MINUTES)
        recent_failures = LoginAttempt.objects.filter(
            email=email, success=False, created_at__gte=window_start
        ).count()
        if recent_failures >= LOGIN_LOCKOUT_THRESHOLD:
            return error_response(
                "Trop de tentatives de connexion échouées. Réessayez dans quelques minutes.",
                status_code=429,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            LoginAttempt.objects.create(email=email, ip_address=ip_address, success=False)
            log_audit_event("login_failed", request=request, metadata={"email": email})
            return error_response("Email ou mot de passe incorrect.", status_code=401)

        if not user.check_password(password):
            LoginAttempt.objects.create(email=email, ip_address=ip_address, success=False)
            log_audit_event("login_failed", user=user, request=request, metadata={"email": email})
            return error_response("Email ou mot de passe incorrect.", status_code=401)

        if not user.is_active:
            return error_response("Compte inactif. Veuillez contacter l'administration.", status_code=403)

        if user.is_banned:
            return error_response(
                f"Ce compte a été banni. Motif : {user.banned_reason or 'non précisé'}.",
                status_code=403,
            )

        if user.role in ("etablissement", "enterprise", "superAdmin"):
            return error_response(
                "Utilisez la connexion web avec double authentification.",
                status_code=403,
            )

        # Authentification réussie
        LoginAttempt.objects.create(email=email, ip_address=ip_address, success=True)
        log_audit_event("login_success", user=user, request=request)
        LoginSession.objects.create(
            user=user, ip_address=ip_address,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        )
        token, _ = Token.objects.get_or_create(user=user)
        data = {
            "token": token.key,
            "user_id": user.id,
            "email": user.email,
            "role": user.role
        }
        return success_response("Connexion réussie.", data)
    

class GoogleLoginView(APIView):
    """POST /users/google-login/ — échange un id_token Google contre un token GConnect."""
    permission_classes = []
    throttle_classes = [LoginThrottle]

    def post(self, request):
        id_token = request.data.get('id_token')
        if not id_token:
            return error_response("id_token requis.", status_code=400)

        try:
            # Vérification du token Google via l'API tokeninfo (pas de dépendance externe requise)
            url = f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}'
            with urllib.request.urlopen(url, timeout=10) as resp:
                import json as _json
                payload = _json.loads(resp.read().decode())
        except Exception:
            return error_response("Token Google invalide ou expiré.", status_code=401)

        # Vérifier l'audience (CLIENT_ID configuré dans settings, ou laisser ouvert en dev)
        google_client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
        if google_client_id and payload.get('aud') != google_client_id:
            return error_response("Token Google non autorisé pour cette application.", status_code=401)

        email = payload.get('email')
        if not email:
            return error_response("Email non fourni par Google.", status_code=400)

        email_verified = payload.get('email_verified') == 'true'
        if not email_verified:
            return error_response("Adresse e-mail Google non vérifiée.", status_code=400)

        # Trouver ou créer l'utilisateur
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Création automatique d'un compte via Google
            first_name = payload.get('given_name', '')
            last_name = payload.get('family_name', '')
            username = email.split('@')[0]
            # Garantir l'unicité du username
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f'{base_username}{counter}'
                counter += 1
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role='student',  # rôle par défaut pour les inscriptions Google
            )
            user.set_unusable_password()
            user.is_active = True
            user.save(update_fields=['is_active'])

        if not user.is_active:
            return error_response("Compte inactif. Veuillez contacter l'administration.", status_code=403)
        if user.is_banned:
            return error_response(
                f"Ce compte a été banni. Motif : {user.banned_reason or 'non précisé'}.",
                status_code=403,
            )

        if user.role in ("etablissement", "enterprise", "superAdmin"):
            return error_response(
                "La connexion Google ne remplace pas la double authentification de cet espace.",
                status_code=403,
            )
        log_audit_event("google_login_success", user=user, request=request)
        token, _ = Token.objects.get_or_create(user=user)
        return success_response("Connexion réussie.", {
            "token": token.key,
            "user_id": user.id,
            "email": user.email,
            "role": user.role,
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if isinstance(request.auth, EstablishmentWebSession):
            return error_response("Utilisez /users/web-logout/ pour ce navigateur.", status_code=400)
        if not request.user.is_authenticated:
            return error_response("Utilisateur non authentifié.", status_code=401)

        try:
            token = Token.objects.get(user=request.user)
            token.delete()
            log_audit_event("logout", user=request.user, request=request)
            return success_response("Déconnexion réussie.")
        except Token.DoesNotExist:
            return error_response("Aucun token trouvé pour cet utilisateur.", status_code=400)


class MeView(APIView):
    """
    GET  /api/v1/users/me/ — profil unifié pour le UserService Flutter.
    PATCH /api/v1/users/me/ — mise à jour de la photo de profil.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, JSONParser]

    def get(self, request):
        user = request.user
        photo_url = None
        if user.photo:
            photo_url = request.build_absolute_uri(user.photo.url)
        cover_image_url = None
        if user.cover_image:
            cover_image_url = request.build_absolute_uri(user.cover_image.url)

        institution_id = None

        from .enterprise_access import enterprise_access
        enterprise, company_owner = enterprise_access(user)
        enterprise_id = enterprise.pk if enterprise else None
        company_name = enterprise.company_name if enterprise else None

        if user.role == 'student':
            try:
                from apps.api.v1.establishments.models import StudentInstitution
                si = StudentInstitution.objects.filter(
                    student=user.student_profile
                ).select_related('institution').first()
                if si:
                    institution_id = si.institution_id
            except Exception:
                pass

        elif user.role == 'alumni':
            try:
                institution_id = user.alumni_profile.institution_id
            except Exception:
                pass

        elif user.role == 'etablissement':
            try:
                institution_id = user.institution_admin_profile.institution_id
            except Exception:
                pass

        data = {
            "id": user.id,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.get_full_name() or user.username,
            "role": user.role,
            "photo_url": photo_url,
            "cover_image_url": cover_image_url,
            "institution_id": institution_id,
            "enterprise_id": enterprise_id,
            "company_name": company_name,
            "enterprise_role": ("owner" if company_owner else "recruiter") if enterprise else None,
        }
        return success_response("Profil récupéré avec succès.", data)

    def patch(self, request):
        """PATCH /api/v1/users/me/ — met à jour (ou supprime) la photo de
        profil et/ou l'image de couverture de l'utilisateur courant."""
        user = request.user

        photo = request.FILES.get('photo')
        cover = request.FILES.get('cover_image')
        remove_photo = str(request.data.get('remove_photo', '')).lower() == 'true'
        remove_cover = str(request.data.get('remove_cover_image', '')).lower() == 'true'
        bio = request.data.get('bio')
        location = request.data.get('location')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        phone_number = request.data.get('phone_number')
        gender = request.data.get('gender')
        date_of_birth = request.data.get('date_of_birth')

        text_fields = [bio, location, first_name, last_name, phone_number, gender, date_of_birth]
        if not any([photo, cover, remove_photo, remove_cover] + [f is not None for f in text_fields]):
            return error_response(
                "Fournir au moins un champ à mettre à jour.",
                status_code=400
            )

        for f, label in ((photo, 'La photo de profil'), (cover, "L'image de couverture")):
            if f is None:
                continue
            error = validate_image_upload(f, label)
            if error:
                return error_response(error, status_code=400)

        update_fields = []

        if photo is not None:
            if user.photo:
                try:
                    user.photo.delete(save=False)
                except Exception:
                    pass
            user.photo = photo
            update_fields.append('photo')
        elif remove_photo and user.photo:
            user.photo.delete(save=False)
            user.photo = None
            update_fields.append('photo')

        if cover is not None:
            if user.cover_image:
                try:
                    user.cover_image.delete(save=False)
                except Exception:
                    pass
            user.cover_image = cover
            update_fields.append('cover_image')
        elif remove_cover and user.cover_image:
            user.cover_image.delete(save=False)
            user.cover_image = None
            update_fields.append('cover_image')

        if bio is not None:
            user.bio = bio
            update_fields.append('bio')
        if location is not None:
            user.location = location
            update_fields.append('location')
        if first_name is not None:
            user.first_name = first_name.strip()
            update_fields.append('first_name')
        if last_name is not None:
            user.last_name = last_name.strip()
            update_fields.append('last_name')
        if phone_number is not None:
            user.phone_number = phone_number.strip()
            update_fields.append('phone_number')

        if update_fields:
            user.save(update_fields=update_fields)

        # Champs sur le profil étudiant/alumni
        if gender is not None:
            if hasattr(user, 'student_profile'):
                try:
                    user.student_profile.gender = gender
                    user.student_profile.save(update_fields=['gender'])
                except Exception:
                    pass
            elif hasattr(user, 'alumni_profile'):
                try:
                    user.alumni_profile.gender = gender
                    user.alumni_profile.save(update_fields=['gender'])
                except Exception:
                    pass

        if date_of_birth is not None and hasattr(user, 'student_profile'):
            try:
                user.student_profile.date_of_birth = date_of_birth
                user.student_profile.save(update_fields=['date_of_birth'])
            except Exception:
                pass

        photo_url = request.build_absolute_uri(user.photo.url) if user.photo else None
        cover_image_url = request.build_absolute_uri(user.cover_image.url) if user.cover_image else None
        return success_response(
            "Profil mis à jour.",
            {
                "photo_url": photo_url, "cover_image_url": cover_image_url,
                "bio": user.bio, "location": user.location,
                "first_name": user.first_name, "last_name": user.last_name,
                "full_name": user.get_full_name() or user.username,
                "phone_number": user.phone_number,
            }
        )


class UserPublicProfileView(APIView):
    """GET /api/v1/users/<user_id>/ — public profile of any user."""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            # Pas de filtre is_active : Post.author est une FK CASCADE, donc si
            # un post existe pour cet auteur, le compte existe forcément en base
            # (actif ou pas — is_active concerne l'activation du compte, pas sa
            # suppression). Filtrer dessus provoquait un faux "introuvable" pour
            # tout auteur pas encore activé ou désactivé après coup.
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return error_response("Utilisateur introuvable.", status_code=404)

        privacy = ProfilePrivacy.for_user(user)
        is_owner = request.user.is_authenticated and request.user.id == user.id

        if not is_owner and not privacy.can_view(request.user, "profile"):
            return error_response("Ce profil est privé.", status_code=403)

        photo_url = (
            request.build_absolute_uri(user.photo.url)
            if user.photo and (is_owner or privacy.can_view(request.user, "photo")) else None
        )
        cover_image_url = (
            request.build_absolute_uri(user.cover_image.url)
            if user.cover_image and (is_owner or privacy.can_view(request.user, "cover")) else None
        )

        # Institution & promotion
        institution_data = None
        promotion_data = None

        if user.role == 'student':
            try:
                from apps.api.v1.establishments.models import StudentInstitution
                si = (StudentInstitution.objects
                      .filter(student=user.student_profile)
                      .select_related('institution')
                      .first())
                if si:
                    inst = si.institution
                    institution_data = {
                        'id': inst.id,
                        'name': inst.name,
                        'logo_url': request.build_absolute_uri(inst.logo.url) if inst.logo else None,
                    }
                # Active promotion membership
                pm = (PromotionMembership.objects
                      .filter(student=user.student_profile, is_approved=True)
                      .select_related('promotion')
                      .exclude(promotion__is_general=True)
                      .first())
                if pm:
                    promotion_data = {'id': pm.promotion.id, 'name': pm.promotion.name}
            except Exception:
                pass

        elif user.role == 'alumni':
            try:
                alumni = user.alumni_profile
                inst = alumni.institution
                institution_data = {
                    'id': inst.id,
                    'name': inst.name,
                    'logo_url': request.build_absolute_uri(inst.logo.url) if inst.logo else None,
                }
                if alumni.promotion:
                    promotion_data = {'id': alumni.promotion.id, 'name': alumni.promotion.name}
            except Exception:
                pass

        elif user.role == 'etablissement':
            try:
                inst = user.institution_admin_profile.institution
                institution_data = {
                    'id': inst.id,
                    'name': inst.name,
                    'logo_url': request.build_absolute_uri(inst.logo.url) if inst.logo else None,
                }
            except Exception:
                pass

        elif user.role == 'enterprise':
            try:
                ent = user.enterprise_profile
                institution_data = {
                    'id': ent.id,
                    'name': ent.company_name,
                    'logo_url': request.build_absolute_uri(ent.logo.url) if ent.logo else None,
                }
            except Exception:
                pass

        # Skills & interests — gérés par la confidentialité (compétences)
        skills = []
        interests = []
        show_skills = is_owner or privacy.can_view(request.user, "skills")
        if show_skills:
            if user.role == 'student':
                try:
                    skills = list(user.student_profile.skills.values('id', 'name'))
                    interests = list(user.student_profile.interests.values('id', 'name'))
                except Exception:
                    pass
            elif user.role == 'alumni':
                try:
                    skills = list(user.alumni_profile.skills.values('id', 'name'))
                    interests = list(user.alumni_profile.interests.values('id', 'name'))
                except Exception:
                    pass

        # Stats / publications — gérées par la confidentialité (publications)
        show_posts = is_owner or privacy.can_view(request.user, "posts")
        posts_count = reactions_received = comments_made = 0
        if show_posts:
            from apps.api.v1.posts.models import Post, Reaction, Comment
            posts_count = Post.objects.filter(author=user, is_archived=False, is_draft=False).count()
            reactions_received = Reaction.objects.filter(post__author=user).count()
            comments_made = Comment.objects.filter(user=user).count()

        # Champs du profil étudiant/alumni (genre, date de naissance)
        gender = None
        date_of_birth = None
        if is_owner:
            if user.role == 'student':
                try:
                    gender = user.student_profile.gender
                    dob = user.student_profile.date_of_birth
                    date_of_birth = dob.isoformat() if dob else None
                except Exception:
                    pass
            elif user.role == 'alumni':
                try:
                    gender = user.alumni_profile.gender
                except Exception:
                    pass

        data = {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'first_name': user.first_name if is_owner else None,
            'last_name': user.last_name if is_owner else None,
            'role': user.role,
            'role_display': user.get_role_display(),
            'photo_url': photo_url,
            'cover_image_url': cover_image_url,
            'bio': user.bio,
            'location': user.location,
            'date_joined': user.date_joined,
            'institution': institution_data,
            'promotion': promotion_data,
            'skills': skills,
            'interests': interests,
            'email': user.email if (is_owner or privacy.can_view(request.user, "email")) else None,
            'phone_number': user.phone_number if (is_owner or privacy.can_view(request.user, "phone")) else None,
            'gender': gender,
            'date_of_birth': date_of_birth,
            'stats': {
                'posts_count': posts_count,
                'reactions_received': reactions_received,
                'comments_made': comments_made,
            },
            'posts_visible': show_posts,
        }
        return success_response("Profil récupéré.", data)


class ChangePasswordView(APIView):
    """
    POST /api/v1/users/me/change-password/  {current_password, new_password}
    Change le mot de passe de l'utilisateur connecté. Révoque le token
    existant et en émet un nouveau immédiatement (le client doit le
    remplacer dans son stockage local) — bonne pratique après un changement
    de mot de passe, sans pour autant déconnecter l'utilisateur en cours de
    session.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')

        if not current_password or not new_password:
            return error_response("current_password et new_password sont requis.", status_code=400)

        user = request.user
        if not user.check_password(current_password):
            return error_response("Mot de passe actuel incorrect.", status_code=400)

        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as exc:
            return error_response(" ".join(exc.messages), status_code=400)

        user.set_password(new_password)
        user.save(update_fields=['password'])

        Token.objects.filter(user=user).delete()
        EstablishmentWebSession.objects.filter(user=user, revoked_at__isnull=True).update(
            revoked_at=timezone.now(),
        )
        log_audit_event("password_changed", user=user, request=request)
        if isinstance(request.auth, EstablishmentWebSession):
            return success_response("Mot de passe mis à jour. Reconnexion nécessaire.", {
                "requires_relogin": True,
            })
        token = Token.objects.create(user=user)
        return success_response("Mot de passe mis à jour.", {"token": token.key})


class ProfilePrivacyView(APIView):
    """
    GET   /api/v1/users/me/privacy/
    PATCH /api/v1/users/me/privacy/
    Réglages de confidentialité par champ de l'utilisateur connecté.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        privacy = ProfilePrivacy.for_user(request.user)
        return success_response("Réglages de confidentialité.", ProfilePrivacySerializer(privacy).data)

    def patch(self, request):
        privacy = ProfilePrivacy.for_user(request.user)
        serializer = ProfilePrivacySerializer(privacy, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_audit_event("privacy_updated", user=request.user, request=request, metadata=dict(request.data))
        return success_response("Réglages de confidentialité mis à jour.", serializer.data)


class LoginSessionsView(APIView):
    """
    GET    /api/v1/users/me/sessions/  — historique des connexions récentes.
    DELETE /api/v1/users/me/sessions/  — révoque le jeton d'accès partagé
           (déconnecte TOUS les appareils, DRF authtoken ne permettant qu'un
           jeton par utilisateur — voir la note sur `LoginSession`).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = LoginSession.objects.filter(user=request.user)[:20]
        data = [
            {
                "id": s.id,
                "ip_address": s.ip_address,
                "user_agent": s.user_agent,
                "created_at": s.created_at,
            }
            for s in sessions
        ]
        return success_response("Historique des connexions.", data)

    def delete(self, request):
        Token.objects.filter(user=request.user).delete()
        EstablishmentWebSession.objects.filter(
            user=request.user, revoked_at__isnull=True,
        ).update(revoked_at=timezone.now())
        log_audit_event("sessions_revoked", user=request.user, request=request)
        if isinstance(request.auth, EstablishmentWebSession):
            return success_response("Toutes les sessions ont été déconnectées.", {
                "requires_relogin": True,
            })
        token = Token.objects.create(user=request.user)
        return success_response(
            "Toutes les sessions ont été déconnectées. Reconnexion nécessaire.",
            {"token": token.key},
        )


class DeleteAccountView(APIView):
    """
    POST /api/v1/users/me/delete-account/  {password}
    Suppression définitive du compte connecté (RGPD) — exige de ressaisir
    le mot de passe pour confirmer. Supprime l'utilisateur ; les objets liés
    suivent les `on_delete` déjà définis sur chaque modèle (CASCADE/SET_NULL).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        password = request.data.get('password')
        if not password:
            return error_response("Le mot de passe est requis pour confirmer la suppression.", status_code=400)

        user = request.user
        if not user.check_password(password):
            return error_response("Mot de passe incorrect.", status_code=400)

        Token.objects.filter(user=user).delete()
        log_audit_event("account_deleted", user=user, request=request, metadata={"email": user.email})
        user.delete()
        return success_response("Compte supprimé définitivement.", {})


class ExportPersonalDataView(APIView):
    """
    GET /api/v1/users/me/export-data/
    Export RGPD des données personnelles de l'utilisateur connecté, au
    format JSON téléchargeable directement par le client.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            "profile": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.get_full_name(),
                "role": user.role,
                "phone_number": user.phone_number,
                "bio": user.bio,
                "location": user.location,
                "date_joined": user.date_joined.isoformat() if user.date_joined else None,
            },
            "login_sessions": [
                {
                    "ip_address": s.ip_address,
                    "user_agent": s.user_agent,
                    "created_at": s.created_at.isoformat(),
                }
                for s in LoginSession.objects.filter(user=user)
            ],
        }

        try:
            from apps.api.v1.posts.models import Post, Comment, Reaction, Bookmark
            data["posts"] = list(Post.objects.filter(author=user).values(
                "id", "title", "content", "post_type", "created_at"
            ))
            data["comments"] = list(Comment.objects.filter(user=user).values("id", "post_id", "content", "created_at"))
            data["reactions"] = list(Reaction.objects.filter(user=user).values("id", "post_id", "kind", "created_at"))
            data["bookmarks"] = list(Bookmark.objects.filter(user=user).values_list("post_id", flat=True))
        except Exception:
            pass

        try:
            from apps.api.v1.networking.models import Connection, Follow
            data["connections"] = list(
                Connection.objects.filter(Q(requester=user) | Q(addressee=user))
                .values("id", "requester_id", "addressee_id", "status", "created_at")
            )
            data["following"] = list(Follow.objects.filter(follower=user).values_list("following_id", flat=True))
        except Exception:
            pass

        log_audit_event("data_exported", user=user, request=request)
        response = JsonResponse(data, json_dumps_params={"indent": 2, "default": str})
        response["Content-Disposition"] = f'attachment; filename="gconnect-donnees-{user.username}.json"'
        return response


class AlumniRegisterView(APIView):
    """POST /api/v1/users/register/alumni/  — auto-inscription d'un alumni.
    L'account est créé inactif ; un admin doit valider le proof_document
    et activer le compte via le backoffice.
    """
    permission_classes = []
    throttle_classes = [RegistrationThrottle]
    parser_classes = [MultiPartParser, JSONParser]

    def post(self, request):
        required = ['email', 'username', 'password', 'first_name', 'last_name', 'gender', 'institution_id']
        missing = [f for f in required if not request.data.get(f)]
        if missing:
            return error_response(f"Champs requis manquants : {', '.join(missing)}", status_code=400)

        email = request.data.get('email', '').strip().lower()
        username = request.data.get('username', '').strip()

        if User.objects.filter(email=email).exists():
            return error_response("Cet email est déjà utilisé.", status_code=400)
        if User.objects.filter(username=username).exists():
            return error_response("Ce nom d'utilisateur est déjà pris.", status_code=400)

        try:
            institution = Institution.objects.get(id=request.data.get('institution_id'))
        except Institution.DoesNotExist:
            return error_response("Établissement introuvable.", status_code=400)

        password = request.data.get('password')
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            validate_password(password)
        except DjangoValidationError as exc:
            return error_response(" ".join(exc.messages), status_code=400)

        proof_document = request.FILES.get('proof_document')
        if not proof_document:
            return error_response("Le document justificatif est requis pour l'inscription alumni.", status_code=400)

        from apps.api.v1.users.models import Alumni
        user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            first_name=request.data.get('first_name'),
            last_name=request.data.get('last_name'),
            phone_number=request.data.get('phone_number', ''),
            role='alumni',
            is_active=False,
        )

        promotion_id = request.data.get('promotion_id')
        promotion = None
        if promotion_id:
            try:
                promotion = Promotion.objects.get(id=promotion_id, institution=institution)
            except Promotion.DoesNotExist:
                pass

        Alumni.objects.create(
            user=user,
            gender=request.data.get('gender'),
            proof_document=proof_document,
            graduation_date=request.data.get('graduation_date') or None,
            institution=institution,
            promotion=promotion,
        )

        return success_response(
            "Votre demande d'inscription alumni a été soumise. "
            "Votre compte sera activé après vérification de vos documents par l'administration.",
            {"user_id": user.id},
            status_code=201,
        )


class GlobalSearchView(APIView):
    """
    GET /api/v1/search/?q=...&type=all|users|posts|establishments|promotions
    Recherche universelle unifiée. `type` restreint à une seule catégorie
    (utile pour un "voir tout" paginé côté client) ; par défaut ('all'),
    renvoie un aperçu borné des quatre catégories. Chaque recherche réussie
    (q >= 2 caractères) est journalisée dans `SearchHistory` pour alimenter
    les suggestions "recherches récentes".
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Q
        from apps.api.v1.posts.models import Post

        q = request.query_params.get('q', '').strip()
        entity_type = request.query_params.get('type', 'all')
        empty = {'users': [], 'posts': [], 'establishments': [], 'promotions': []}
        if len(q) < 2:
            return success_response("Résultats", empty)

        limit = 12 if entity_type == 'all' else 30
        data = dict(empty)

        # ── Utilisateurs ──────────────────────────────────────────────────────
        if entity_type in ('all', 'users'):
            candidates = list(User.objects.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(username__icontains=q)
            ).exclude(id=request.user.id)[:limit * 2])  # marge avant filtrage confidentialité

            candidate_ids = [u.id for u in candidates]
            priv_map = {
                p.user_id: p
                for p in ProfilePrivacy.objects.filter(user_id__in=candidate_ids)
            }

            users_data = []
            for u in candidates:
                privacy = priv_map.get(u.id) or ProfilePrivacy(user=u)
                if not privacy.can_view(request.user, "profile"):
                    continue
                photo = (
                    request.build_absolute_uri(u.photo.url)
                    if getattr(u, 'photo', None) and u.photo and privacy.can_view(request.user, "photo")
                    else None
                )
                users_data.append({
                    'id': u.id,
                    'name': u.get_full_name() or u.username,
                    'username': u.username,
                    'role': u.role,
                    'photo': photo,
                })
                if len(users_data) >= limit:
                    break
            data['users'] = users_data

        # ── Publications ──────────────────────────────────────────────────────
        if entity_type in ('all', 'posts'):
            posts = (Post.objects
                .filter(
                    Q(content__icontains=q) | Q(title__icontains=q),
                    is_draft=False,
                    is_archived=False,
                )
                .select_related('author')
                .order_by('-created_at')[:limit])

            posts_data = []
            for p in posts:
                author_photo = request.build_absolute_uri(p.author.photo.url) if getattr(p.author, 'photo', None) and p.author.photo else None
                posts_data.append({
                    'id': p.id,
                    'title': p.title or '',
                    'content': p.content[:150],
                    'author_id': p.author.id,
                    'author_name': p.author.get_full_name() or p.author.username,
                    'author_photo': author_photo,
                    'post_type': p.post_type,
                    'created_at': p.created_at.isoformat(),
                })
            data['posts'] = posts_data

        # ── Établissements ────────────────────────────────────────────────────
        if entity_type in ('all', 'establishments'):
            institutions = (Institution.objects
                .filter(Q(name__icontains=q) | Q(acronym__icontains=q))
                .select_related('city')[:limit])

            establishments_data = []
            for i in institutions:
                logo = request.build_absolute_uri(i.logo.url) if getattr(i, 'logo', None) and i.logo else None
                establishments_data.append({
                    'id': i.id,
                    'name': i.name,
                    'acronym': i.acronym or '',
                    'logo_url': logo,
                    'city_name': i.city.name if i.city else '',
                })
            data['establishments'] = establishments_data

        # ── Promotions ─────────────────────────────────────────────────────────
        if entity_type in ('all', 'promotions'):
            promotions = (Promotion.objects
                .filter(Q(name__icontains=q) | Q(department__icontains=q))
                .select_related('institution')[:limit])

            promotions_data = []
            for pr in promotions:
                promotions_data.append({
                    'id': pr.id,
                    'name': pr.name,
                    'institution_id': pr.institution_id,
                    'institution_name': pr.institution.name if pr.institution else '',
                    'institution_acronym': pr.institution.acronym if pr.institution else '',
                    'department': pr.department or '',
                    'level': pr.level or '',
                    'year': pr.year,
                })
            data['promotions'] = promotions_data

        SearchHistory.record(request.user, q)
        return success_response("Résultats", data)


class SearchHistoryView(APIView):
    """
    GET    /api/v1/users/me/search-history/  — 10 recherches récentes.
    DELETE /api/v1/users/me/search-history/  — efface tout l'historique.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = SearchHistory.objects.filter(user=request.user)[:10]
        return success_response("Historique de recherche.", [
            {"id": h.id, "query": h.query, "created_at": h.created_at} for h in items
        ])

    def delete(self, request):
        SearchHistory.objects.filter(user=request.user).delete()
        return success_response("Historique de recherche effacé.", {})


# from django.contrib.auth import get_user_model

# User = get_user_model()
# try:

#     user = User.objects.get(username='admin') # ou email='admin@gmail.com'

#     print(f"User found: {user.username}, email: {user.email}")

#     if user.check_password('Passer123'): # Remplacez par le mot de passe que vous pensez avoir utilisé

#         print("Password matches!")

#     else:

#         print("Password DOES NOT match!")
# except User.DoesNotExist:

#     print("User 'admin' does not exist.")
