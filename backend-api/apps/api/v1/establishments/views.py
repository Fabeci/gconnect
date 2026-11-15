"""
G-Connect - Establishments Views
ViewSets pour l'application des établissements
"""

from rest_framework import viewsets, generics, status, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from apps.api.v1.subscriptions.quotas import lock_institution, require_available_school_seat

from apps.api.v1.establishments.models import (
    Institution, Promotion, PromotionMembership, AlumniPromotionMembership,
    PromotionJoinRequest, StudentInstitution, AlumniInstitution,
    StudentAccountOrder
)
from apps.api.v1.establishments.serializers import (
    InstitutionListSerializer, InstitutionDetailSerializer, InstitutionCreateSerializer,
    PromotionListSerializer, PromotionDetailSerializer, PromotionCreateSerializer,
    PromotionMembershipSerializer, PromotionJoinRequestSerializer,
    PromotionJoinRequestCreateSerializer, StudentAccountOrderSerializer,
    MemberDirectorySerializer,
)
from apps.api.v1.establishments.pagination import GenerousResultsSetPagination, StandardResultsSetPagination
from apps.api.v1.core.validators import validate_image_upload
from apps.api.v1.establishments.permissions import IsInstitutionManager, IsInstitutionScopedManager
from apps.api.v1.core.permissions import IsSuperAdmin


class InstitutionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les établissements
    """

    pagination_class = StandardResultsSetPagination

    def list(self, request, *args, **kwargs):
        """Liste paginée, avec un dict d'avatars de membres précalculé en
        deux requêtes groupées (pas une par établissement) pour éviter le N+1."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        target = page if page is not None else queryset

        context = self.get_serializer_context()
        context['avatars_map'] = self._build_avatars_map(target)
        context['my_membership_map'] = self._build_membership_map(target)

        serializer = InstitutionListSerializer(target, many=True, context=context)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def _build_membership_map(self, institutions):
        """{institution_id: membership_dict|None} pour l'utilisateur courant —
        1 requête bornée max (pas une par établissement), lu par
        InstitutionMembershipMixin.get_my_membership via le contexte."""
        ids = [inst.id for inst in institutions]
        user = self.request.user
        if not ids or not user or not user.is_authenticated:
            return {}

        result = {}

        if hasattr(user, 'student_profile'):
            links = StudentInstitution.objects.filter(
                student=user.student_profile, institution_id__in=ids
            )
            for link in links:
                result[link.institution_id] = {
                    'type': 'student',
                    'joined_at': link.joined_at,
                    'is_primary': link.is_primary,
                    'is_active': link.is_active,
                }
        elif hasattr(user, 'alumni_profile'):
            links = AlumniInstitution.objects.filter(
                alumni=user.alumni_profile, institution_id__in=ids
            )
            for link in links:
                result[link.institution_id] = {
                    'type': 'alumni',
                    'joined_at': link.joined_at,
                    'is_active': link.is_active,
                }
        elif hasattr(user, 'institution_admin_profile'):
            admin_institution_id = user.institution_admin_profile.institution_id
            if admin_institution_id in ids:
                result[admin_institution_id] = {'type': 'admin', 'is_active': True}

        return result

    def _build_avatars_map(self, institutions):
        """{institution_id: [avatar_url, ...]} — jusqu'à 3 par établissement,
        calculé en 2 requêtes groupées quelle que soit la taille de la page."""
        ids = [inst.id for inst in institutions]
        if not ids:
            return {}

        request = self.request
        result = {i: [] for i in ids}

        student_links = StudentInstitution.objects.filter(
            institution_id__in=ids
        ).select_related('student__user').order_by('id')
        for link in student_links:
            bucket = result[link.institution_id]
            if len(bucket) >= 3:
                continue
            photo = getattr(link.student.user, 'photo', None)
            if photo:
                bucket.append(request.build_absolute_uri(photo.url) if request else photo.url)

        alumni_links = AlumniInstitution.objects.filter(
            institution_id__in=ids
        ).select_related('alumni__user').order_by('id')
        for link in alumni_links:
            bucket = result[link.institution_id]
            if len(bucket) >= 3:
                continue
            photo = getattr(link.alumni.user, 'photo', None)
            if photo:
                bucket.append(request.build_absolute_uri(photo.url) if request else photo.url)

        return result

    def get_serializer_class(self):
        if self.action == 'list':
            return InstitutionListSerializer
        if self.action == 'create':
            return InstitutionCreateSerializer
        return InstitutionDetailSerializer

    def get_permissions(self):
        """Public reads; only the linked institution admin may edit or delete."""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action == 'create':
            return [IsSuperAdmin()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsInstitutionManager()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Retourne les établissements actifs"""
        queryset = Institution.objects.filter(is_active=True)
        
        # Filtres optionnels
        country = self.request.query_params.get('country', None)
        city = self.request.query_params.get('city', None)
        search = self.request.query_params.get('search', None)
        
        if country:
            queryset = queryset.filter(country__name__icontains=country)
        
        if city:
            queryset = queryset.filter(city__name__icontains=city)
        
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(acronym__icontains=search)
            )
        
        # order_by explicite requis : Institution n'a pas d'ordre par défaut,
        # et une pagination sur une queryset non ordonnée donne des résultats
        # incohérents d'une page à l'autre (doublons/oublis).
        return queryset.annotate(
            members_count=Count('students', distinct=True) + Count('alumni', distinct=True),
            promotions_count=Count('promotions', distinct=True)
        ).order_by('-members_count', 'name')
    
    @action(detail=False, methods=['post'])
    @transaction.atomic
    def join(self, request):
        """Rejoindre un établissement via code ou QR UUID"""
        code = request.data.get('code', None)
        qr_uuid = request.data.get('qr_uuid', None)
        
        if not code and not qr_uuid:
            return Response(
                {'error': 'Code ou QR UUID requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Chercher l'établissement
        institution = None
        if code:
            institution = Institution.objects.filter(text_code=code, is_active=True).first()
        elif qr_uuid:
            institution = Institution.objects.filter(qr_uuid=qr_uuid, is_active=True).first()
        
        if not institution:
            return Response(
                {'error': 'Établissement non trouvé ou inactif'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Serialise membership additions for a school: concurrent joins must
        # never exceed the current subscription's active seat allowance.
        lock_institution(institution.pk)
        
        # Ajouter l'utilisateur selon son profil
        user = request.user
        
        if hasattr(user, 'student_profile'):
            student = user.student_profile
            if not StudentInstitution.objects.filter(student=student, institution=institution).exists() and user.is_active:
                require_available_school_seat(institution)
            link, created = StudentInstitution.objects.get_or_create(
                student=student,
                institution=institution
            )
            
            if created:
                return Response({
                    'status': 'établissement rejoint',
                    'institution': institution.name,
                    'message': 'Vous avez été automatiquement ajouté à la promotion générale'
                })
            else:
                return Response(
                    {'error': 'Vous êtes déjà membre de cet établissement'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        elif hasattr(user, 'alumni_profile'):
            alumni = user.alumni_profile
            if not AlumniInstitution.objects.filter(alumni=alumni, institution=institution).exists() and user.is_active:
                require_available_school_seat(institution)
            link, created = AlumniInstitution.objects.get_or_create(
                alumni=alumni,
                institution=institution
            )
            
            if created:
                return Response({
                    'status': 'établissement rejoint',
                    'institution': institution.name
                })
            else:
                return Response(
                    {'error': 'Vous êtes déjà membre de cet établissement'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(
            {'error': 'Profil incomplet. Seuls les étudiants et alumni peuvent rejoindre'},
            status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Quitter un établissement (étudiant ou alumni uniquement)."""
        institution = self.get_object()
        user = request.user

        if hasattr(user, 'institution_admin_profile') and \
                user.institution_admin_profile.institution_id == institution.id:
            return Response(
                {'error': "Les administrateurs ne peuvent pas quitter leur établissement depuis cette action."},
                status=status.HTTP_403_FORBIDDEN
            )

        if hasattr(user, 'student_profile'):
            student = user.student_profile
            link = StudentInstitution.objects.filter(student=student, institution=institution).first()
            if not link:
                return Response(
                    {'error': "Vous n'êtes pas membre de cet établissement."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Nettoyer les adhésions aux promotions de cet établissement
            # (générale + spécifiques) pour ne pas laisser de lignes orphelines.
            PromotionMembership.objects.filter(
                student=student, promotion__institution=institution
            ).delete()
            link.delete()
            return Response({'status': 'établissement quitté', 'institution': institution.name})

        if hasattr(user, 'alumni_profile'):
            alumni = user.alumni_profile
            link = AlumniInstitution.objects.filter(alumni=alumni, institution=institution).first()
            if not link:
                return Response(
                    {'error': "Vous n'êtes pas membre de cet établissement."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            AlumniPromotionMembership.objects.filter(
                alumni=alumni, promotion__institution=institution
            ).delete()
            link.delete()
            return Response({'status': 'établissement quitté', 'institution': institution.name})

        return Response(
            {'error': "Vous n'êtes pas membre de cet établissement."},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_active(self, request, pk=None):
        """Active ou désactive un établissement dans le fil d'actualité de l'utilisateur.
        Répond avec {'is_active': bool, 'institution_id': int}."""
        institution = self.get_object()
        user = request.user

        if hasattr(user, 'student_profile'):
            link = StudentInstitution.objects.filter(
                student=user.student_profile, institution=institution
            ).first()
            if not link:
                return Response(
                    {'error': "Vous n'êtes pas membre de cet établissement."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            link.is_active = not link.is_active
            link.save(update_fields=['is_active'])
            return Response({'is_active': link.is_active, 'institution_id': institution.id})

        if hasattr(user, 'alumni_profile'):
            link = AlumniInstitution.objects.filter(
                alumni=user.alumni_profile, institution=institution
            ).first()
            if not link:
                return Response(
                    {'error': "Vous n'êtes pas membre de cet établissement."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            link.is_active = not link.is_active
            link.save(update_fields=['is_active'])
            return Response({'is_active': link.is_active, 'institution_id': institution.id})

        return Response(
            {'error': "Action non disponible pour votre profil."},
            status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=True, methods=['patch'], parser_classes=[MultiPartParser, FormParser])
    def images(self, request, pk=None):
        """Met à jour (ou supprime) le logo / l'image de couverture.
        Réservé à l'admin de cet établissement (ou superAdmin)."""
        institution = self.get_object()
        user = request.user

        is_admin = (
            hasattr(user, 'institution_admin_profile')
            and user.institution_admin_profile.institution_id == institution.id
        )
        is_super = getattr(user, 'role', None) == 'superAdmin'
        if not (is_admin or is_super):
            return Response(
                {'error': "Seul un administrateur de cet établissement peut modifier ses images."},
                status=status.HTTP_403_FORBIDDEN
            )

        logo = request.FILES.get('logo')
        cover = request.FILES.get('cover_image')
        remove_logo = str(request.data.get('remove_logo', '')).lower() == 'true'
        remove_cover = str(request.data.get('remove_cover_image', '')).lower() == 'true'

        for f, label in ((logo, 'Le logo'), (cover, "L'image de couverture")):
            if f is None:
                continue
            error = validate_image_upload(f, label)
            if error:
                return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)

        if logo is not None:
            institution.logo = logo
        elif remove_logo:
            institution.logo.delete(save=False)
            institution.logo = None

        if cover is not None:
            institution.cover_image = cover
        elif remove_cover:
            institution.cover_image.delete(save=False)
            institution.cover_image = None

        institution.save()

        serializer = InstitutionDetailSerializer(institution, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def promotions(self, request, pk=None):
        """Liste des promotions d'un établissement"""
        institution = self.get_object()
        promotions = institution.promotions.all().order_by('is_general', 'name')

        serializer = PromotionListSerializer(
            promotions, many=True, context={'request': request}
        )
        return Response({
            'institution': institution.name,
            'promotions_count': promotions.count(),
            'promotions': serializer.data,
        })
    
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Statistiques de l'établissement"""
        institution = self.get_object()
        
        students_count = StudentInstitution.objects.filter(institution=institution).count()
        alumni_count = AlumniInstitution.objects.filter(institution=institution).count()
        promotions_count = institution.promotions.count()
        general_promo = institution.general_promotion
        general_members = general_promo.members.filter(is_approved=True).count() if general_promo else 0
        
        return Response({
            'institution': institution.name,
            'students': students_count,
            'alumni': alumni_count,
            'total_members': students_count + alumni_count,
            'promotions': promotions_count,
            'general_promotion_members': general_members
        })


class PromotionViewSet(viewsets.ModelViewSet):
    """ViewSet pour les promotions"""
    permission_classes = [IsAuthenticated]
    pagination_class = GenerousResultsSetPagination

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsInstitutionScopedManager()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.action == 'list':
            return PromotionListSerializer
        if self.action == 'create':
            return PromotionCreateSerializer
        return PromotionDetailSerializer

    def get_queryset(self):
        queryset = Promotion.objects.all().select_related('institution')

        # Restreindre aux établissements actifs de l'utilisateur connecté.
        # Les promos restent dans le périmètre de l'utilisateur : si un
        # établissement est désactivé, ses promos (y compris la générale)
        # disparaissent du catalogue.
        user = self.request.user
        if user and user.is_authenticated:
            if user.role == 'superAdmin':
                pass  # Plateforme : visibilité transversale.
            elif hasattr(user, 'student_profile'):
                active_ids = StudentInstitution.objects.filter(
                    student=user.student_profile, is_active=True
                ).values_list('institution_id', flat=True)
                queryset = queryset.filter(institution_id__in=active_ids)
            elif hasattr(user, 'alumni_profile'):
                active_ids = AlumniInstitution.objects.filter(
                    alumni=user.alumni_profile, is_active=True
                ).values_list('institution_id', flat=True)
                if not active_ids.exists() and user.alumni_profile.institution:
                    # Fallback FK directe si aucun lien AlumniInstitution actif
                    queryset = queryset.filter(
                        institution=user.alumni_profile.institution
                    )
                else:
                    queryset = queryset.filter(institution_id__in=active_ids)
            elif user.role == 'etablissement' and hasattr(user, 'institution_admin_profile'):
                inst = user.institution_admin_profile.institution
                if inst:
                    queryset = queryset.filter(institution=inst)

        # Filtres optionnels
        institution = self.request.query_params.get('institution', None)
        is_general = self.request.query_params.get('is_general', None)

        if institution:
            queryset = queryset.filter(institution_id=institution)

        if is_general is not None:
            queryset = queryset.filter(is_general=is_general.lower() == 'true')

        return queryset.order_by('-is_general', 'name', 'id')

    def list(self, request, *args, **kwargs):
        """Liste paginée des promotions, avec avatars de membres et
        my_membership précalculés en requêtes groupées (pas une par
        promotion) pour éviter le N+1."""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        target = page if page is not None else queryset

        context = self.get_serializer_context()
        context['avatars_map'] = self._build_avatars_map(target)
        context['my_membership_map'] = self._build_membership_map(target, request.user)
        serializer = PromotionListSerializer(target, many=True, context=context)

        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def _build_membership_map(self, promotions, user):
        """{promotion_id: {...}} — remplace le `.filter().first()` par
        promotion que ferait PromotionListSerializer.get_my_membership() si
        appelé sans ce contexte précalculé."""
        ids = [p.id for p in promotions]
        if not ids or not user or not user.is_authenticated:
            return {}

        result = {}
        if hasattr(user, 'student_profile'):
            for m in PromotionMembership.objects.filter(
                student=user.student_profile, promotion_id__in=ids
            ):
                result[m.promotion_id] = {
                    'is_member': True, 'is_approved': m.is_approved,
                    'is_delegate': m.is_delegate, 'is_active': m.is_active,
                    'joined_at': m.joined_at,
                }
        elif hasattr(user, 'alumni_profile'):
            for m in AlumniPromotionMembership.objects.filter(
                alumni=user.alumni_profile, promotion_id__in=ids
            ):
                result[m.promotion_id] = {
                    'is_member': True, 'is_approved': m.is_approved,
                    'is_active': m.is_active, 'joined_at': m.joined_at,
                }
        return result

    def _build_avatars_map(self, promotions):
        """{promotion_id: [avatar_url, ...]} — jusqu'à 3 par promotion,
        calculé en 2 requêtes groupées quel que soit le nombre de promotions."""
        ids = [p.id for p in promotions]
        if not ids:
            return {}

        request = self.request
        result = {i: [] for i in ids}

        student_links = PromotionMembership.objects.filter(
            promotion_id__in=ids, is_approved=True
        ).select_related('student__user').order_by('id')
        for link in student_links:
            bucket = result[link.promotion_id]
            if len(bucket) >= 3:
                continue
            photo = getattr(link.student.user, 'photo', None)
            if photo:
                bucket.append(request.build_absolute_uri(photo.url) if request else photo.url)

        alumni_links = AlumniPromotionMembership.objects.filter(
            promotion_id__in=ids, is_approved=True
        ).select_related('alumni__user').order_by('id')
        for link in alumni_links:
            bucket = result[link.promotion_id]
            if len(bucket) >= 3:
                continue
            photo = getattr(link.alumni.user, 'photo', None)
            if photo:
                bucket.append(request.build_absolute_uri(photo.url) if request else photo.url)

        return result

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_active(self, request, pk=None):
        """Active ou désactive une promotion dans le fil d'actualité de
        l'utilisateur (même logique que `InstitutionViewSet.toggle_active`).
        Répond avec {'is_active': bool, 'promotion_id': int}."""
        promotion = self.get_object()
        user = request.user

        if hasattr(user, 'student_profile'):
            link = PromotionMembership.objects.filter(
                student=user.student_profile, promotion=promotion
            ).first()
            if not link:
                return Response(
                    {'error': "Vous n'êtes pas membre de cette promotion."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            link.is_active = not link.is_active
            link.save(update_fields=['is_active'])
            return Response({'is_active': link.is_active, 'promotion_id': promotion.id})

        if hasattr(user, 'alumni_profile'):
            link = AlumniPromotionMembership.objects.filter(
                alumni=user.alumni_profile, promotion=promotion
            ).first()
            if not link:
                return Response(
                    {'error': "Vous n'êtes pas membre de cette promotion."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            link.is_active = not link.is_active
            link.save(update_fields=['is_active'])
            return Response({'is_active': link.is_active, 'promotion_id': promotion.id})

        return Response(
            {'error': "Action non disponible pour votre profil."},
            status=status.HTTP_403_FORBIDDEN
        )

    @action(detail=True, methods=['post'])
    def request_join(self, request, pk=None):
        """Demander à rejoindre une promotion"""
        promotion = self.get_object()
        motivation = request.data.get('motivation', '')
        
        # Vérifier que c'est un étudiant ou alumni
        user = request.user
        student = getattr(user, 'student_profile', None)
        alumni = getattr(user, 'alumni_profile', None)
        
        if not student and not alumni:
            return Response(
                {'error': 'Seuls les étudiants et alumni peuvent rejoindre des promotions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Vérifier que l'utilisateur est membre de l'établissement
        if student:
            if not StudentInstitution.objects.filter(
                student=student,
                institution=promotion.institution
            ).exists():
                return Response(
                    {'error': 'Vous devez d\'abord rejoindre l\'établissement'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif alumni:
            if not AlumniInstitution.objects.filter(
                alumni=alumni,
                institution=promotion.institution
            ).exists():
                return Response(
                    {'error': 'Vous devez d\'abord rejoindre l\'établissement'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Créer la demande
        join_request, created = PromotionJoinRequest.objects.get_or_create(
            student=student if student else None,
            alumni=alumni if alumni else None,
            promotion=promotion,
            defaults={'motivation': motivation}
        )
        
        if created:
            return Response({
                'status': 'demande créée',
                'promotion': promotion.name,
                'message': 'Votre demande sera examinée par un administrateur ou un délégué'
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'error': 'Une demande existe déjà pour cette promotion'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Récupérer les membres d'une promotion"""
        promotion = self.get_object()
        
        student_memberships = promotion.members.filter(is_approved=True)
        alumni_memberships = promotion.alumni_members.filter(is_approved=True)
        
        from apps.api.v1.establishments.serializers import (
            PromotionMembershipSerializer, AlumniPromotionMembershipSerializer
        )
        
        student_serializer = PromotionMembershipSerializer(student_memberships, many=True)
        alumni_serializer = AlumniPromotionMembershipSerializer(alumni_memberships, many=True)
        
        return Response({
            "students": student_serializer.data,
            "alumni": alumni_serializer.data,
            "total_count": student_memberships.count() + alumni_memberships.count()
        })


class PromotionJoinRequestViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """ViewSet pour les demandes d'adhésion"""
    permission_classes = [IsAuthenticated]
    pagination_class = GenerousResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return PromotionJoinRequestCreateSerializer
        return PromotionJoinRequestSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PromotionJoinRequest.objects.none()

        user = self.request.user

        # Superadmin : toutes les demandes, admin : seulement son établissement.
        if user.role == 'superAdmin':
            return PromotionJoinRequest.objects.all()
        if user.role == 'etablissement' and hasattr(user, 'institution_admin_profile'):
            return PromotionJoinRequest.objects.filter(
                promotion__institution=user.institution_admin_profile.institution
            )
        
        # Délégué : demandes de ses promotions
        if hasattr(user, 'student_profile'):
            delegate_promotions = PromotionMembership.objects.filter(
                student=user.student_profile,
                is_delegate=True
            ).values_list('promotion_id', flat=True)
            
            return PromotionJoinRequest.objects.filter(
                Q(promotion_id__in=delegate_promotions) |
                Q(student__user=user) |
                Q(alumni__user=user)
            )
        
        # Utilisateur normal : ses propres demandes
        return PromotionJoinRequest.objects.filter(
            Q(student__user=user) | Q(alumni__user=user)
        )
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Accepter une demande"""
        join_request = self.get_object()
        
        if not join_request.can_be_approved_by(request.user):
            return Response(
                {'error': 'Vous n\'avez pas la permission d\'approuver cette demande'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            join_request.accept(request.user)
            return Response({
                'status': 'demande acceptée',
                'promotion': join_request.promotion.name
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Rejeter une demande"""
        join_request = self.get_object()
        reason = request.data.get('reason', '')
        
        if not join_request.can_be_approved_by(request.user):
            return Response(
                {'error': 'Vous n\'avez pas la permission de rejeter cette demande'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            join_request.reject(request.user, reason)
            return Response({
                'status': 'demande rejetée',
                'reason': reason
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class PromotionMembershipViewSet(viewsets.ModelViewSet):
    """ViewSet pour les adhésions"""
    permission_classes = [IsAuthenticated]
    serializer_class = PromotionMembershipSerializer
    pagination_class = GenerousResultsSetPagination

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'make_delegate'):
            return [IsInstitutionScopedManager()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        # Membership creation must go through the validated join/approval flows.
        return Response({'error': 'Utilisez la procédure d’adhésion.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return PromotionMembership.objects.none()
        user = self.request.user
        promotion = self.request.query_params.get('promotion')

        # Base : promotions dont l'utilisateur est membre ou administrateur
        if user.role == 'superAdmin':
            queryset = PromotionMembership.objects.all().select_related('student__user', 'promotion')
        elif user.role == 'etablissement' and hasattr(user, 'institution_admin_profile'):
            institution_id = user.institution_admin_profile.institution_id
            queryset = PromotionMembership.objects.filter(
                promotion__institution_id=institution_id
            ).select_related('student__user', 'promotion')
        elif hasattr(user, 'student_profile'):
            user_promotion_ids = PromotionMembership.objects.filter(
                student=user.student_profile, is_approved=True
            ).values_list('promotion_id', flat=True)
            queryset = PromotionMembership.objects.filter(
                promotion_id__in=user_promotion_ids
            ).select_related('student__user', 'promotion')
        else:
            queryset = PromotionMembership.objects.none()

        if promotion:
            queryset = queryset.filter(promotion_id=promotion)
        return queryset
    
    @action(detail=True, methods=['post'])
    def make_delegate(self, request, pk=None):
        """Nommer un membre comme délégué"""
        membership = self.get_object()
        
        # Vérifier les permissions (admin uniquement)
        if not hasattr(request.user, 'institution_admin_profile'):
            return Response(
                {'error': 'Seuls les admins peuvent nommer des délégués'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not membership.is_approved:
            return Response(
                {'error': 'Le membre doit d\'abord être approuvé'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        membership.is_delegate = True
        membership.save()
        
        return Response({
            'status': 'délégué nommé',
            'member': membership.student.user.get_full_name()
        })


class StudentAccountOrderViewSet(viewsets.ModelViewSet):
    """ViewSet pour les commandes de comptes"""
    permission_classes = [IsAuthenticated]
    serializer_class = StudentAccountOrderSerializer
    pagination_class = GenerousResultsSetPagination

    def get_permissions(self):
        if self.action == 'create':
            return [IsInstitutionScopedManager()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsSuperAdmin()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        # The institution is a security boundary: never accept another
        # institution ID, even though creation has no existing object to check.
        if request.user.role != 'superAdmin':
            linked_id = request.user.institution_admin_profile.institution_id
            if str(request.data.get('institution')) != str(linked_id):
                return Response({'error': 'Établissement non autorisé.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        if self.request.user.role == 'superAdmin':
            serializer.save()
        else:
            # Orders are only *requested* here; price/approval is decided
            # by the platform. A school must not self-approve free accounts.
            serializer.save(
                institution=self.request.user.institution_admin_profile.institution,
                status='pending', price_per_account=0,
            )

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return StudentAccountOrder.objects.none()

        user = self.request.user

        # Admin : toutes les commandes
        if user.role == 'superAdmin':
            return StudentAccountOrder.objects.all()
        
        # Admin établissement : commandes de son établissement
        if user.role == 'etablissement' and hasattr(user, 'institution_admin_profile'):
            return StudentAccountOrder.objects.filter(
                institution=user.institution_admin_profile.institution
            )

        return StudentAccountOrder.objects.none()


# ── Suggestions de membres ────────────────────────────────────────────────────

class SuggestedMembersView(APIView):
    """
    GET /api/v1/establishments/suggestions/

    Retourne jusqu'à 10 membres approuvés de l'institution du user connecté,
    en excluant le user lui-même. Fonctionne pour tous les rôles :
    student, alumni, etablissement.

    Chaque membre inclut cover_image_url/institution_name/promotion_name
    (pour la carte "même établissement" de l'accueil) ainsi que
    `relation_previews` : jusqu'à 3 relations mutuelles *réelles* (connexions
    acceptées communes avec le user connecté) — calculées en requêtes
    groupées, jamais une requête par candidat.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        import random
        from collections import defaultdict
        from apps.api.v1.core.responses import success_response
        from apps.api.v1.networking.models import Connection

        institution = self._get_institution(request.user)
        if not institution:
            return success_response("Aucune institution trouvée", [])

        general = institution.general_promotion
        if not general:
            return success_response("Aucune promotion générale", [])

        # Étudiants membres de la promotion générale (hors utilisateur courant)
        student_ms = list(
            PromotionMembership.objects
            .filter(promotion=general, is_approved=True)
            .exclude(student__user=request.user)
            .select_related('student__user')
        )
        # Alumni membres de la promotion générale (hors utilisateur courant)
        alumni_ms = list(
            AlumniPromotionMembership.objects
            .filter(promotion=general, is_approved=True)
            .exclude(alumni__user=request.user)
            .select_related('alumni__user')
        )

        # Candidats unifiés : (user, role_label), mélangés puis limités à 10
        candidates = (
            [(m.student.user, 'Délégué(e)' if m.is_delegate else 'Étudiant(e)') for m in student_ms]
            + [(m.alumni.user, 'Alumni') for m in alumni_ms]
        )
        random.shuffle(candidates)
        candidates = candidates[:10]

        candidate_ids = [u.id for u, _ in candidates]

        # Relations mutuelles — 1 requête groupée
        my_connections = Connection.connected_ids(request.user)
        relevant_ids = my_connections | set(candidate_ids)
        adjacency = defaultdict(set)
        if relevant_ids:
            for a, b in Connection.objects.filter(status=Connection.Status.ACCEPTED).filter(
                Q(requester_id__in=relevant_ids) | Q(addressee_id__in=relevant_ids)
            ).values_list('requester_id', 'addressee_id'):
                adjacency[a].add(b)
                adjacency[b].add(a)

        mutual_ids_by_candidate = {
            cid: my_connections & adjacency.get(cid, set()) for cid in candidate_ids
        }
        preview_ids = {pid for ids in mutual_ids_by_candidate.values() for pid in list(ids)[:3]}
        preview_users = type(request.user).objects.in_bulk(preview_ids)

        result = []
        for u, role_label in candidates:
            photo = (
                request.build_absolute_uri(u.photo.url)
                if getattr(u, 'photo', None) else None
            )
            cover = (
                request.build_absolute_uri(u.cover_image.url)
                if getattr(u, 'cover_image', None) else None
            )

            mutual_ids = mutual_ids_by_candidate.get(u.id, set())
            previews = []
            for pid in list(mutual_ids)[:3]:
                pu = preview_users.get(pid)
                if not pu:
                    continue
                previews.append({
                    'id': pu.id,
                    'name': pu.get_full_name() or pu.username,
                    'photo': (
                        request.build_absolute_uri(pu.photo.url)
                        if getattr(pu, 'photo', None) else None
                    ),
                })

            result.append({
                'id': u.id,
                'name': u.get_full_name() or u.username,
                'photo': photo,
                'cover_image_url': cover,
                'role': u.role,
                'role_label': role_label,
                'institution_name': institution.name,
                'promotion_name': general.name,
                'relations_count': len(mutual_ids),
                'relation_previews': previews,
            })

        return success_response("Membres suggérés", result)

    def _get_institution(self, user):
        """Retourne l'institution active de l'utilisateur (ou la première active)."""
        try:
            if user.role == 'student':
                si = (StudentInstitution.objects
                      .filter(student=user.student_profile, is_active=True)
                      .select_related('institution')
                      .first())
                return si.institution if si else None
            if user.role == 'alumni':
                ai = AlumniInstitution.objects.filter(
                    alumni=user.alumni_profile, is_active=True
                ).select_related('institution').first()
                if ai:
                    return ai.institution
                # Fallback FK directe si aucun AlumniInstitution is_active
                return user.alumni_profile.institution
            if user.role == 'etablissement':
                return user.institution_admin_profile.institution
        except Exception:
            pass
        return None


class AllMembersView(generics.ListAPIView):
    """
    GET /api/v1/establishments/members/

    Annuaire complet et paginé des membres de l'établissement de
    l'utilisateur connecté — page dédiée "Voir tout" de l'accueil
    (le widget d'accueil, lui, reste sur /suggestions/, inchangé).

    Query params :
    - `search` : filtre nom, prénom, promotion ou établissement (icontains)
    - `page`, `page_size` : pagination standard (StandardResultsSetPagination)
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    serializer_class = MemberDirectorySerializer
    queryset = PromotionMembership.objects.none()  # requis par GenericAPIView (schéma/OPTIONS) ; list() ne l'utilise pas

    def _member_list(self):
        """Une ligne par utilisateur (pas par PromotionMembership) : un membre
        inscrit à la fois à la promotion générale et à une promotion
        spécifique doit apparaître une seule fois, représenté par sa
        promotion la plus parlante (spécifique de préférence, générale en
        repli). Le volume par établissement reste modeste (dizaines à
        quelques centaines de lignes) donc dédupliquer en mémoire après UNE
        requête groupée reste largement préférable à du N+1.
        Seules les institutions actives de l'utilisateur sont incluses."""
        user = self.request.user
        active_institution_ids = self._get_active_institution_ids(user)
        if not active_institution_ids:
            return []

        qs = (
            PromotionMembership.objects
            .filter(promotion__institution_id__in=active_institution_ids, is_approved=True)
            .exclude(student__user=user)
            .select_related('student__user', 'promotion__institution')
        )

        search = self.request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(student__user__first_name__icontains=search) |
                Q(student__user__last_name__icontains=search) |
                Q(student__user__username__icontains=search) |
                Q(promotion__name__icontains=search) |
                Q(promotion__department__icontains=search) |
                Q(promotion__institution__name__icontains=search) |
                Q(promotion__institution__acronym__icontains=search)
            )

        best_by_user = {}
        for m in qs:
            uid = m.student.user_id
            current = best_by_user.get(uid)
            # Préférer une promotion spécifique à la promotion générale.
            if current is None or (current.promotion.is_general and not m.promotion.is_general):
                best_by_user[uid] = m

        members = list(best_by_user.values())
        members.sort(key=lambda m: (m.student.user.first_name or '', m.student.user.last_name or ''))
        return members

    def _get_active_institution_ids(self, user):
        """Retourne la liste des institution_id actifs selon le rôle."""
        try:
            if hasattr(user, 'student_profile'):
                ids = list(
                    StudentInstitution.objects.filter(
                        student=user.student_profile, is_active=True
                    ).values_list('institution_id', flat=True)
                )
                return ids
            if hasattr(user, 'alumni_profile'):
                ids = list(
                    AlumniInstitution.objects.filter(
                        alumni=user.alumni_profile, is_active=True
                    ).values_list('institution_id', flat=True)
                )
                if ids:
                    return ids
                # Fallback FK directe
                inst = user.alumni_profile.institution
                return [inst.id] if inst else []
            if hasattr(user, 'institution_admin_profile'):
                inst = user.institution_admin_profile.institution
                return [inst.id] if inst else []
        except Exception:
            pass
        return []

    def list(self, request, *args, **kwargs):
        members = self._member_list()
        page = self.paginate_queryset(members)
        target = page if page is not None else members

        context = self.get_serializer_context()
        context['previews_map'], context['relations_count_map'] = self._build_previews(target)

        serializer = self.get_serializer(target, many=True, context=context)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def _build_previews(self, memberships):
        """({user_id: [{id,name,photo}, ...]}, {promotion_id: count}) —
        calculé en 1 requête groupée par promotion distincte (ici une seule
        dans la pratique : la promotion générale de l'établissement), jamais
        une requête par membre affiché."""
        promo_ids = {m.promotion_id for m in memberships}
        if not promo_ids:
            return {}, {}

        request = self.request
        pool_by_promo = {}
        counts_by_promo = {}
        for promo_id in promo_ids:
            candidates = (
                PromotionMembership.objects
                .filter(promotion_id=promo_id, is_approved=True)
                .exclude(student__user=request.user)
                .select_related('student__user')
                .order_by('id')[:15]
            )
            pool = []
            for c in candidates:
                u = c.student.user
                pool.append({
                    'id': u.id,
                    'name': u.get_full_name() or u.username,
                    'photo': (
                        request.build_absolute_uri(u.photo.url)
                        if getattr(u, 'photo', None) else None
                    ),
                })
            pool_by_promo[promo_id] = pool
            counts_by_promo[promo_id] = (
                PromotionMembership.objects
                .filter(promotion_id=promo_id, is_approved=True)
                .exclude(student__user=request.user)
                .count()
            )

        previews_map = {}
        for m in memberships:
            pool = pool_by_promo.get(m.promotion_id, [])
            uid = m.student.user_id
            previews_map[uid] = [p for p in pool if p['id'] != uid][:3]

        return previews_map, counts_by_promo

    def _get_institution(self, user):
        try:
            if user.role == 'student':
                si = (StudentInstitution.objects
                      .filter(student=user.student_profile)
                      .select_related('institution')
                      .first())
                return si.institution if si else None
            if user.role == 'alumni':
                return user.alumni_profile.institution
            if user.role == 'etablissement':
                return user.institution_admin_profile.institution
        except Exception:
            pass
        return None
