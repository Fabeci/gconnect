"""
G-Connect - Establishments Serializers (ADAPTÉS AUX MODELS ACTUELS)

- Compatible avec les models fournis (Institution, Promotion, Memberships, Orders, etc.)
- Corrige les incohérences :
  * InstitutionAdmin n'a pas "position" -> retiré
  * StudentAccountOrder.total_price_display -> source corrigée
  * PromotionCreateSerializer : pas de check "is_general" si le champ n'est pas exposé
  * Ville/Pays (cities_light) : renvoi en texte + id optionnel
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.api.v1.establishments.models import (
    Institution, StudentInstitution, AlumniInstitution,
    Promotion, PromotionMembership, AlumniPromotionMembership,
    PromotionJoinRequest, StudentAccountOrder
)

User = get_user_model()


# ==================== USER BASIC ====================

class UserBasicSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les informations utilisateur"""
    full_name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        ref_name = "EstablishmentUserBasic"
        fields = ["id", "username", "full_name", "email", "photo_url", "role"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_photo_url(self, obj):
        request = self.context.get("request")
        if getattr(obj, "photo", None):
            return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url
        return None


# ==================== INSTITUTION SERIALIZERS ====================

class InstitutionMembershipMixin:
    """
    Résout le statut d'adhésion de l'utilisateur courant à un établissement
    (student/alumni/admin). Partagé entre InstitutionListSerializer et
    InstitutionDetailSerializer pour garantir que la liste ET le détail
    exposent `my_membership` de façon cohérente (même logique que
    PostTypeDetailsMixin dans posts/serializers.py).

    En mode liste, `context['my_membership_map']` (institution_id -> info)
    est précalculé en une requête bornée par InstitutionViewSet.list() pour
    éviter un N+1 — get_my_membership l'utilise en priorité s'il est présent.
    """

    def get_my_membership(self, obj):
        membership_map = self.context.get("my_membership_map")
        if membership_map is not None:
            return membership_map.get(obj.id)

        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return None

        user = request.user

        # Étudiant
        if hasattr(user, "student_profile"):
            membership = StudentInstitution.objects.filter(
                student=user.student_profile,
                institution=obj
            ).first()
            if membership:
                return {
                    "type": "student",
                    "joined_at": membership.joined_at,
                    "is_primary": membership.is_primary,
                    "is_active": membership.is_active,
                }

        # Alumni
        if hasattr(user, "alumni_profile"):
            membership = AlumniInstitution.objects.filter(
                alumni=user.alumni_profile,
                institution=obj
            ).first()
            if membership:
                return {
                    "type": "alumni",
                    "joined_at": membership.joined_at,
                    "is_active": membership.is_active,
                }

        # Admin établissement (InstitutionAdmin a uniquement user + institution)
        if hasattr(user, "institution_admin_profile"):
            if user.institution_admin_profile.institution_id == obj.id:
                return {
                    "type": "admin",
                    "is_active": True,
                }

        return None


class InstitutionListSerializer(InstitutionMembershipMixin, serializers.ModelSerializer):
    """Serializer pour la liste des établissements (vue compacte)

    members_count/promotions_count sont lus depuis les annotations déjà
    calculées par InstitutionViewSet.get_queryset() (une seule requête pour
    toute la page) plutôt que recalculés par ligne — évite un N+1.
    """
    members_count = serializers.IntegerField(read_only=True, default=0)
    promotions_count = serializers.IntegerField(read_only=True, default=0)
    logo_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    member_avatars = serializers.SerializerMethodField()
    my_membership = serializers.SerializerMethodField()

    city_id = serializers.IntegerField(source="city.id", read_only=True, default=None)
    city_name = serializers.CharField(source="city.name", read_only=True, default=None)

    country_id = serializers.IntegerField(source="country.id", read_only=True, default=None)
    country_name = serializers.CharField(source="country.name", read_only=True, default=None)

    location_display = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = [
            "id", "name", "acronym", "description",
            "logo_url", "cover_image_url",
            "city_id", "city_name",
            "country_id", "country_name",
            "location_display",
            "members_count", "promotions_count", "member_avatars",
            "is_active", "created_at", "my_membership",
        ]

    def get_logo_url(self, obj):
        if not obj.logo:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url

    def get_cover_image_url(self, obj):
        if not obj.cover_image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.cover_image.url) if request else obj.cover_image.url

    def get_member_avatars(self, obj):
        """Jusqu'à 3 URLs de photo de membres, lues depuis le dict précalculé
        par la vue (context['avatars_map']) — pas de requête par ligne."""
        avatars_map = self.context.get("avatars_map") or {}
        return avatars_map.get(obj.id, [])

    def get_location_display(self, obj):
        parts = []
        if obj.city:
            parts.append(getattr(obj.city, "name", str(obj.city)))
        if obj.country:
            parts.append(getattr(obj.country, "name", str(obj.country)))
        return ", ".join(parts) if parts else None


class InstitutionDetailSerializer(InstitutionMembershipMixin, serializers.ModelSerializer):
    """Serializer détaillé pour un établissement"""
    logo_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    qr_code_url = serializers.SerializerMethodField()
    statistics = serializers.SerializerMethodField()
    general_promotion = serializers.SerializerMethodField()
    my_membership = serializers.SerializerMethodField()
    administrators = serializers.SerializerMethodField()
    recent_posts = serializers.SerializerMethodField()
    upcoming_events = serializers.SerializerMethodField()
    suggested_institutions = serializers.SerializerMethodField()

    city_id = serializers.IntegerField(source="city.id", read_only=True, default=None)
    city_name = serializers.CharField(source="city.name", read_only=True, default=None)

    region_id = serializers.IntegerField(source="region.id", read_only=True, default=None)
    region_name = serializers.CharField(source="region.name", read_only=True, default=None)

    country_id = serializers.IntegerField(source="country.id", read_only=True, default=None)
    country_name = serializers.CharField(source="country.name", read_only=True, default=None)

    class Meta:
        model = Institution
        fields = [
            "id", "name", "acronym", "slug",
            "text_code", "qr_uuid", "qr_code_url",
            "description", "address",
            "city_id", "city_name",
            "region_id", "region_name",
            "country_id", "country_name",
            "phone", "email", "website",
            "logo_url", "cover_image_url",
            "established_year", "accreditation",
            "latitude", "longitude",
            "is_active", "created_at", "updated_at",
            "statistics", "general_promotion", "my_membership",
            "administrators", "recent_posts", "upcoming_events",
            "suggested_institutions",
        ]
        read_only_fields = ["id", "text_code", "qr_uuid", "slug", "created_at", "updated_at"]

    def get_logo_url(self, obj):
        if not obj.logo:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url

    def get_cover_image_url(self, obj):
        if not obj.cover_image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.cover_image.url) if request else obj.cover_image.url

    def get_qr_code_url(self, obj):
        if not obj.qr_uuid:
            return None
        return f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={obj.qr_uuid}"

    def get_statistics(self, obj):
        students_count = StudentInstitution.objects.filter(institution=obj).count()
        alumni_count = AlumniInstitution.objects.filter(institution=obj).count()

        gp = obj.general_promotion
        gp_members = gp.members_count if gp else 0

        return {
            "students": students_count,
            "alumni": alumni_count,
            "total_members": students_count + alumni_count,
            "promotions": obj.promotions.count(),
            "general_promotion_members": gp_members,
            "posts_count": obj.posts.count(),
            "opportunities_count": obj.posts.filter(post_type="opportunity").count(),
            "events_count": obj.posts.filter(post_type="event").count(),
        }

    def get_administrators(self, obj):
        """Admins de l'établissement (users.InstitutionAdmin)."""
        from apps.api.v1.users.models import InstitutionAdmin

        admins = InstitutionAdmin.objects.filter(institution=obj).select_related("user")
        return UserBasicSerializer(
            [a.user for a in admins], many=True, context=self.context
        ).data

    def get_recent_posts(self, obj):
        """5 dernières publications de l'établissement (tous types confondus)."""
        from apps.api.v1.posts.serializers import PostListSerializer

        posts = obj.posts.filter(is_archived=False).select_related(
            "author", "opportunity", "opportunity__enterprise", "event", "project"
        ).order_by("-created_at")[:5]
        return PostListSerializer(posts, many=True, context=self.context).data

    def get_upcoming_events(self, obj):
        """Événements à venir organisés par l'établissement."""
        from django.utils import timezone
        from apps.api.v1.posts.serializers import PostListSerializer

        posts = obj.posts.filter(
            is_archived=False, post_type="event", event__starts_at__gte=timezone.now()
        ).select_related("author", "event").order_by("event__starts_at")[:5]
        return PostListSerializer(posts, many=True, context=self.context).data

    def get_suggested_institutions(self, obj):
        """Autres établissements actifs, triés par nombre de membres."""
        from django.db.models import Count

        others = Institution.objects.filter(is_active=True).exclude(id=obj.id).annotate(
            members_count=Count("students", distinct=True) + Count("alumni", distinct=True),
            promotions_count=Count("promotions", distinct=True),
        ).order_by("-members_count")[:5]
        return InstitutionListSerializer(others, many=True, context=self.context).data

    def get_general_promotion(self, obj):
        promo = obj.general_promotion
        if not promo:
            return None
        return {
            "id": promo.id,
            "name": promo.name,
            "members_count": promo.members_count,
            "has_discussion_group": hasattr(promo, "discussion_group"),
        }

class InstitutionCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer / modifier un établissement"""

    class Meta:
        model = Institution
        fields = [
            "name", "acronym", "description", "address",
            "city", "region", "country",
            "phone", "email", "website",
            "logo", "cover_image",
            "established_year", "accreditation",
            "latitude", "longitude",
        ]

    def validate_name(self, value):
        if Institution.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("Un établissement avec ce nom existe déjà.")
        return value
    

class InstitutionMembersSerializer(serializers.ModelSerializer):
    students = serializers.SerializerMethodField()
    alumni = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = ["id", "name", "students", "alumni", "total_members"]

    def get_students(self, obj):
        qs = StudentInstitution.objects.filter(institution=obj).select_related("student__user")
        users = [x.student.user for x in qs]
        return UserBasicSerializer(users, many=True, context=self.context).data

    def get_alumni(self, obj):
        qs = AlumniInstitution.objects.filter(institution=obj).select_related("alumni__user")
        users = [x.alumni.user for x in qs]
        return UserBasicSerializer(users, many=True, context=self.context).data

    def get_total_members(self, obj):
        students = StudentInstitution.objects.filter(institution=obj).count()
        alumni = AlumniInstitution.objects.filter(institution=obj).count()
        return students + alumni


# ==================== PROMOTION SERIALIZERS ====================

class PromotionListSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source="institution.name", read_only=True)
    institution_acronym = serializers.CharField(source="institution.acronym", read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    members_count = serializers.IntegerField(read_only=True)
    pending_requests_count = serializers.IntegerField(read_only=True)
    member_avatars = serializers.SerializerMethodField()

    type_display = serializers.SerializerMethodField()
    my_membership = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            "id", "name", "institution", "institution_name", "institution_acronym",
            "is_general", "type_display",
            "year", "department", "level", "description",
            "cover_image_url",
            "members_count", "pending_requests_count", "member_avatars",
            "my_membership",
            "created_at",
        ]

    def get_member_avatars(self, obj):
        """Jusqu'à 3 URLs de photo de membres, lues depuis le dict précalculé
        par la vue (context['avatars_map']) — pas de requête par ligne."""
        avatars_map = self.context.get("avatars_map") or {}
        return avatars_map.get(obj.id, [])

    def get_cover_image_url(self, obj):
        if not obj.cover_image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.cover_image.url) if request else obj.cover_image.url

    def get_type_display(self, obj):
        if obj.is_general:
            return {
                "type": "general",
                "label": "🌍 Promotion Générale",
                "description": "Tous les membres de l'établissement",
            }
        return {
            "type": "specific",
            "label": "🎯 Promotion Spécifique",
            "description": f'{obj.level or ""} {obj.department or ""}'.strip(),
        }

    def get_my_membership(self, obj):
        membership_map = self.context.get("my_membership_map")
        if membership_map is not None:
            return membership_map.get(obj.id, {"is_member": False})

        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return None

        user = request.user

        if hasattr(user, "student_profile"):
            membership = PromotionMembership.objects.filter(
                student=user.student_profile,
                promotion=obj
            ).first()
            if membership:
                return {
                    "is_member": True,
                    "is_approved": membership.is_approved,
                    "is_delegate": membership.is_delegate,
                    "is_active": membership.is_active,
                    "joined_at": membership.joined_at,
                }

        if hasattr(user, "alumni_profile"):
            membership = AlumniPromotionMembership.objects.filter(
                alumni=user.alumni_profile,
                promotion=obj
            ).first()
            if membership:
                return {
                    "is_member": True,
                    "is_approved": membership.is_approved,
                    "is_active": membership.is_active,
                    "joined_at": membership.joined_at,
                }

        return {"is_member": False}


class PromotionDetailSerializer(serializers.ModelSerializer):
    institution = InstitutionListSerializer(read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    statistics = serializers.SerializerMethodField()
    discussion_group = serializers.SerializerMethodField()
    my_membership = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            "id", "name", "institution", "is_general", "description",
            "year", "department", "level",
            "cover_image_url",
            "created_at", "updated_at",
            "statistics", "discussion_group", "my_membership",
        ]
        read_only_fields = ["id", "is_general", "created_at", "updated_at"]

    def get_cover_image_url(self, obj):
        if not obj.cover_image:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.cover_image.url) if request else obj.cover_image.url

    def get_statistics(self, obj):
        students = obj.members.filter(is_approved=True).count()
        alumni = obj.alumni_members.filter(is_approved=True).count()
        delegates = obj.members.filter(is_approved=True, is_delegate=True).count()
        pending = obj.join_requests.filter(status="pending").count()

        return {
            "total_members": students + alumni,
            "students": students,
            "alumni": alumni,
            "delegates": delegates,
            "pending_requests": pending,
        }

    def get_discussion_group(self, obj):
        if not hasattr(obj, "discussion_group"):
            return None

        group = obj.discussion_group
        conversation = group.conversation

        return {
            "id": conversation.id,
            "name": conversation.name,
            "participants_count": conversation.memberships.filter(is_active=True).count(),
            "created_at": group.created_at,
        }

    def get_my_membership(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return None

        user = request.user

        if hasattr(user, "student_profile"):
            membership = PromotionMembership.objects.filter(
                student=user.student_profile,
                promotion=obj
            ).first()
            if membership:
                return {
                    "is_member": True,
                    "is_approved": membership.is_approved,
                    "is_delegate": membership.is_delegate,
                    "is_active": membership.is_active,
                    "joined_at": membership.joined_at,
                    "approved_by": (
                        UserBasicSerializer(membership.approved_by, context=self.context).data
                        if membership.approved_by else None
                    ),
                    "approved_at": membership.approved_at,
                }

        if hasattr(user, "alumni_profile"):
            membership = AlumniPromotionMembership.objects.filter(
                alumni=user.alumni_profile,
                promotion=obj
            ).first()
            if membership:
                return {
                    "is_member": True,
                    "is_approved": membership.is_approved,
                    "is_active": membership.is_active,
                    "joined_at": membership.joined_at,
                    "approved_by": (
                        UserBasicSerializer(membership.approved_by, context=self.context).data
                        if membership.approved_by else None
                    ),
                    "approved_at": membership.approved_at,
                }

        return {"is_member": False}


class PromotionCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer une promotion (spécifique)"""

    class Meta:
        model = Promotion
        fields = ["institution", "name", "description", "year", "department", "level", "cover_image"]

    def validate(self, data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        institution = data.get("institution")

        if user and user.is_authenticated and user.role == "superAdmin":
            return data
        admin = getattr(user, "institution_admin_profile", None)
        if (
            not user or not user.is_authenticated or user.role != "etablissement"
            or not admin or not admin.institution.is_active
            or admin.institution_id != getattr(institution, "pk", None)
        ):
            raise serializers.ValidationError({
                "institution": "Vous ne pouvez créer des promotions que pour votre établissement."
            })
        return data


# ==================== MEMBERSHIPS ====================

class PromotionMembershipSerializer(serializers.ModelSerializer):
    student = UserBasicSerializer(source="student.user", read_only=True)
    promotion_name = serializers.CharField(source="promotion.name", read_only=True)
    approved_by_user = UserBasicSerializer(source="approved_by", read_only=True)
    status_display = serializers.SerializerMethodField()
    relation_previews = serializers.SerializerMethodField()

    class Meta:
        model = PromotionMembership
        fields = [
            "id", "student", "promotion", "promotion_name",
            "is_approved", "is_delegate", "is_active", "status_display",
            "approved_by_user", "approved_at", "joined_at",
            "relation_previews",
        ]
        read_only_fields = ["id", "promotion", "joined_at", "approved_at"]

    def get_status_display(self, obj):
        if obj.is_approved:
            if obj.is_delegate:
                return {"status": "delegate", "label": "⭐ Délégué", "color": "gold"}
            return {"status": "approved", "label": "✅ Approuvé", "color": "green"}
        return {"status": "pending", "label": "⏳ En attente", "color": "orange"}

    def get_relation_previews(self, obj):
        request = self.context.get("request")
        others = (
            PromotionMembership.objects
            .filter(promotion=obj.promotion, is_approved=True)
            .exclude(id=obj.id)
            .select_related("student__user")[:3]
        )
        result = []
        for m in others:
            user = m.student.user
            photo = None
            if getattr(user, "photo", None):
                photo = (
                    request.build_absolute_uri(user.photo.url)
                    if request else user.photo.url
                )
            result.append({
                "id": user.id,
                "name": user.get_full_name() or user.username,
                "photo": photo,
            })
        return result


class AlumniPromotionMembershipSerializer(serializers.ModelSerializer):
    alumni = UserBasicSerializer(source="alumni.user", read_only=True)
    promotion_name = serializers.CharField(source="promotion.name", read_only=True)
    approved_by_user = UserBasicSerializer(source="approved_by", read_only=True)
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = AlumniPromotionMembership
        fields = [
            "id", "alumni", "promotion", "promotion_name",
            "is_approved", "is_active", "status_display",
            "approved_by_user", "approved_at", "joined_at",
        ]
        read_only_fields = ["id", "joined_at", "approved_at"]

    def get_status_display(self, obj):
        if obj.is_approved:
            return {"status": "approved", "label": "✅ Approuvé", "color": "green"}
        return {"status": "pending", "label": "⏳ En attente", "color": "orange"}


# ==================== JOIN REQUESTS ====================

class PromotionJoinRequestSerializer(serializers.ModelSerializer):
    requester = serializers.SerializerMethodField()
    promotion_name = serializers.CharField(source="promotion.name", read_only=True)
    promotion_institution = serializers.CharField(source="promotion.institution.name", read_only=True)
    processed_by_user = UserBasicSerializer(source="processed_by", read_only=True)
    status_display = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()

    class Meta:
        model = PromotionJoinRequest
        fields = [
            "id", "requester", "promotion", "promotion_name",
            "promotion_institution", "motivation", "status",
            "status_display", "processed_by_user", "processed_at",
            "rejection_reason", "created_at", "can_approve",
        ]
        read_only_fields = ["id", "status", "processed_by_user", "processed_at", "created_at"]

    def get_requester(self, obj):
        user = obj.student.user if obj.student else obj.alumni.user
        data = UserBasicSerializer(user, context=self.context).data
        data["type"] = "student" if obj.student else "alumni"
        return data

    def get_status_display(self, obj):
        statuses = {
            "pending": {"status": "pending", "label": "⏳ En attente", "color": "orange"},
            "accepted": {"status": "accepted", "label": "✅ Acceptée", "color": "green"},
            "rejected": {"status": "rejected", "label": "❌ Rejetée", "color": "red"},
        }
        return statuses.get(obj.status, statuses["pending"])

    def get_can_approve(self, obj):
        request = self.context.get("request")
        if not request or not request.user:
            return False
        return obj.can_be_approved_by(request.user)


class PromotionJoinRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionJoinRequest
        fields = ["promotion", "motivation"]

    def validate_promotion(self, value):
        if value.is_general:
            raise serializers.ValidationError("Vous êtes automatiquement membre de la promotion générale.")
        return value

    def validate(self, data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        promotion = data.get("promotion")

        student = getattr(user, "student_profile", None)
        alumni = getattr(user, "alumni_profile", None)

        if not student and not alumni:
            raise serializers.ValidationError("Seuls les étudiants et alumni peuvent rejoindre des promotions.")

        if student:
            if not StudentInstitution.objects.filter(student=student, institution=promotion.institution).exists():
                raise serializers.ValidationError("Vous devez d'abord rejoindre l'établissement.")
            if PromotionJoinRequest.objects.filter(student=student, promotion=promotion).exists():
                raise serializers.ValidationError("Une demande existe déjà pour cette promotion.")

        if alumni:
            if not AlumniInstitution.objects.filter(alumni=alumni, institution=promotion.institution).exists():
                raise serializers.ValidationError("Vous devez d'abord rejoindre l'établissement.")
            if PromotionJoinRequest.objects.filter(alumni=alumni, promotion=promotion).exists():
                raise serializers.ValidationError("Une demande existe déjà pour cette promotion.")

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        if hasattr(user, "student_profile"):
            validated_data["student"] = user.student_profile
        elif hasattr(user, "alumni_profile"):
            validated_data["alumni"] = user.alumni_profile

        return super().create(validated_data)


# ==================== ACCOUNT ORDERS ====================

class StudentAccountOrderSerializer(serializers.ModelSerializer):
    institution_name = serializers.CharField(source="institution.name", read_only=True)

    total_price_display = serializers.CharField(read_only=True)

    remaining_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    usage_percentage = serializers.SerializerMethodField()

    class Meta:
        model = StudentAccountOrder
        fields = [
            "id", "institution", "institution_name", "year",
            "quantity", "price_per_account",
            "total_price_display",
            "status", "status_display",
            "used_accounts", "remaining_display",
            "usage_percentage", "created_at",
        ]
        read_only_fields = ["id", "used_accounts", "created_at"]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("La quantité doit être strictement positive.")
        return value

    def validate_price_per_account(self, value):
        if value < 0:
            raise serializers.ValidationError("Le prix ne peut pas être négatif.")
        return value

    def get_remaining_display(self, obj):
        remaining = obj.remaining
        total = obj.quantity or 0
        percentage = (obj.used_accounts / total * 100) if total > 0 else 0

        if percentage < 50:
            indicator = "🟢"
        elif percentage < 80:
            indicator = "🟡"
        else:
            indicator = "🔴"

        return {
            "remaining": remaining,
            "total": total,
            "indicator": indicator,
            "text": f"{remaining} / {total}",
        }

    def get_status_display(self, obj):
        statuses = {
            "pending": {"status": "pending", "label": "⏳ En attente", "color": "orange"},
            "approved": {"status": "approved", "label": "✅ Approuvée", "color": "green"},
            "rejected": {"status": "rejected", "label": "❌ Rejetée", "color": "red"},
        }
        return statuses.get(obj.status, statuses["pending"])

    def get_usage_percentage(self, obj):
        if not obj.quantity:
            return 0
        return round((obj.used_accounts / obj.quantity) * 100, 1)


# ==================== STATS SERIALIZERS ====================

class InstitutionStatsSerializer(serializers.Serializer):
    total_members = serializers.IntegerField()
    students = serializers.IntegerField()
    alumni = serializers.IntegerField()
    promotions = serializers.IntegerField()
    general_promotion_members = serializers.IntegerField()
    posts_count = serializers.IntegerField(required=False)
    opportunities_count = serializers.IntegerField(required=False)
    events_count = serializers.IntegerField(required=False)


class PromotionStatsSerializer(serializers.Serializer):
    total_members = serializers.IntegerField()
    students = serializers.IntegerField()
    alumni = serializers.IntegerField()
    delegates = serializers.IntegerField()
    pending_requests = serializers.IntegerField()
    posts_count = serializers.IntegerField(required=False)
    engagement_rate = serializers.FloatField(required=False)


# ==================== ANNUAIRE DES MEMBRES (page "Voir tout") ====================

class MemberDirectorySerializer(serializers.Serializer):
    """
    Sérialise une `PromotionMembership` en carte "membre" pour la page
    dédiée /establishments/members/ (accueil → "Voir tout").

    `relations_count` et `relation_previews` sont lus depuis
    `context['previews_map']`/`context['relations_count_map']`, précalculés
    par la vue en une requête groupée par promotion (pas une par membre).
    """
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    role_label = serializers.SerializerMethodField()
    institution_id = serializers.SerializerMethodField()
    institution_name = serializers.SerializerMethodField()
    institution_acronym = serializers.SerializerMethodField()
    promotion_id = serializers.IntegerField(source="promotion.id")
    promotion_name = serializers.CharField(source="promotion.name")
    relations_count = serializers.SerializerMethodField()
    relation_previews = serializers.SerializerMethodField()

    def _user(self, obj):
        return obj.student.user

    def _abs(self, file_field):
        if not file_field:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(file_field.url) if request else file_field.url

    def get_id(self, obj):
        return self._user(obj).id

    def get_name(self, obj):
        u = self._user(obj)
        return u.get_full_name() or u.username

    def get_photo_url(self, obj):
        return self._abs(getattr(self._user(obj), "photo", None))

    def get_cover_image_url(self, obj):
        return self._abs(getattr(self._user(obj), "cover_image", None))

    def get_role(self, obj):
        return self._user(obj).role

    def get_role_label(self, obj):
        return "Délégué(e)" if obj.is_delegate else "Étudiant(e)"

    def get_institution_id(self, obj):
        return obj.promotion.institution_id

    def get_institution_name(self, obj):
        return obj.promotion.institution.name

    def get_institution_acronym(self, obj):
        return obj.promotion.institution.acronym

    def get_relations_count(self, obj):
        counts_map = self.context.get("relations_count_map") or {}
        return counts_map.get(obj.promotion_id, 0)

    def get_relation_previews(self, obj):
        previews_map = self.context.get("previews_map") or {}
        return previews_map.get(self._user(obj).id, [])
