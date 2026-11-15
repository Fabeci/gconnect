"""
G-Connect - Posts Views (COMPLETS)
ViewSets pour l'application des publications avec toutes les fonctionnalités
"""

import datetime
import logging

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db import transaction
from django.db.models import Q, Count, Prefetch, F, Exists, OuterRef, Subquery
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

logger = logging.getLogger(__name__)

from apps.api.v1.posts.pagination import PostPagination
from apps.api.v1.establishments.pagination import GenerousResultsSetPagination

from apps.api.v1.posts.models import (
    Post, PostAttachment, Opportunity, Event, Project,
    Reaction, Comment, CommentLike, Share, Bookmark, Application, RSVP
)
from apps.api.v1.subscriptions.quotas import consume_enterprise_publication
from .serializers import (
    PostListSerializer, PostDetailSerializer, PostCreateSerializer,
    PostUpdateSerializer,
    OpportunitySerializer, OpportunityCreateSerializer,
    EventSerializer, ProjectSerializer,
    ReactionSerializer, CommentSerializer, CommentCreateSerializer,
    ApplicationSerializer, RSVPSerializer, BookmarkSerializer,
    PostAttachmentSerializer,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_user_institution(user):
    """Résout l'établissement de l'auteur depuis son profil."""
    if hasattr(user, 'student_profile'):
        return user.student_profile.institutions.first()
    if hasattr(user, 'alumni_profile'):
        return user.alumni_profile.institution
    if hasattr(user, 'institution_admin_profile'):
        return user.institution_admin_profile.institution
    return None


def visible_post_filter(user, prefix=''):
    """
    Reconstruit la même règle de visibilité que PostViewSet.get_queryset()
    (public / promotion générale limitée aux établissements actifs /
    promotion spécifique limitée aux promotions actives) sous forme de `Q`,
    réutilisable pour filtrer un modèle lié via `post` (Opportunity, Event,
    Project) — `prefix` vaut alors `'post__'`. Avant ce correctif,
    EventViewSet et ProjectViewSet n'appliquaient AUCUN filtre de visibilité
    (tout utilisateur authentifié voyait tous les événements/projets, y
    compris ceux ciblant une promotion spécifique d'un autre établissement).
    """
    def f(field):
        return f"{prefix}{field}"

    public_posts = Q(**{f("audience"): Post.Audience.PUBLIC})
    general_posts = Q(**{f("audience"): Post.Audience.GENERAL_PROMOTION})
    specific_posts = Q(**{f("audience"): Post.Audience.SPECIFIC_PROMOTION})

    if not user or not user.is_authenticated:
        return public_posts

    if hasattr(user, 'student_profile'):
        from apps.api.v1.establishments.models import StudentInstitution
        active_institution_ids = StudentInstitution.objects.filter(
            student=user.student_profile, is_active=True, seat_enabled=True
        ).values_list('institution_id', flat=True)
        general_posts &= Q(**{f("institution__id__in"): active_institution_ids})

        user_promotions = user.student_profile.promotion_memberships.filter(
            is_approved=True, is_active=True,
            promotion__institution_id__in=active_institution_ids,
        ).values_list('promotion_id', flat=True)
        specific_posts &= Q(**{f("promotion_targets__id__in"): user_promotions})
    elif hasattr(user, 'alumni_profile'):
        from apps.api.v1.establishments.models import AlumniInstitution
        active_ai = AlumniInstitution.objects.filter(
            alumni=user.alumni_profile, is_active=True, seat_enabled=True
        ).values_list('institution_id', flat=True)
        if AlumniInstitution.objects.filter(alumni=user.alumni_profile).exists():
            general_posts &= Q(**{f("institution__id__in"): active_ai})
        elif user.alumni_profile.institution:
            general_posts &= Q(**{f("institution"): user.alumni_profile.institution})

        user_promotions = user.alumni_profile.promotion_memberships.filter(
            is_approved=True, is_active=True,
        ).values_list('promotion_id', flat=True)
        specific_posts &= Q(**{f("promotion_targets__id__in"): user_promotions})
    elif hasattr(user, 'institution_admin_profile'):
        admin_institution = user.institution_admin_profile.institution
        if admin_institution:
            general_posts &= Q(**{f("institution"): admin_institution})
            specific_posts &= Q(**{f("promotion_targets__institution"): admin_institution})

    return public_posts | general_posts | specific_posts


def _create_nested(model_class, post, data):
    """
    Crée un objet imbriqué (Opportunity, Event, Project) lié au post.
    Filtre les champs inconnus et les relations M2M pour éviter les erreurs ORM.
    """
    if not data or not isinstance(data, dict):
        return
    reserved = {'id', 'pk', 'post'}
    allowed = {
        f.name
        for f in model_class._meta.get_fields()
        if hasattr(f, 'name')
        and f.name not in reserved
        and not getattr(f, 'many_to_many', False)
        and not getattr(f, 'one_to_many', False)
    }
    clean = {k: v for k, v in data.items() if k in allowed}
    try:
        model_class.objects.create(post=post, **clean)
    except Exception as exc:
        logger.warning('Nested %s creation failed for post %s: %s',
                       model_class.__name__, post.pk, exc)
        raise


# ==================== POST VIEWSET ====================

class PostViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les publications
    
    list: Feed des publications (filtré selon visibilité)
    retrieve: Détails d'une publication
    create: Créer une publication
    update/partial_update: Modifier une publication
    destroy: Supprimer une publication
    """
    
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    pagination_class = PostPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content', 'author__username']
    ordering_fields = ['created_at', 'views_count', 'reactions_count']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Retourne les posts visibles par l'utilisateur
        Filtrage selon l'audience
        """
        user = self.request.user
        
        queryset = Post.objects.filter(
            is_archived=False,
            is_draft=False,
            is_hidden_by_admin=False,
        ).select_related(
            'author', 'institution',
            'opportunity', 'opportunity__enterprise', 'event', 'project'
        ).prefetch_related(
            'attachments', 'promotion_targets', 'reactions', 'comments'
        )
        
        # Filtrer selon la visibilité
        if user.is_authenticated:
            # Posts publics
            public_posts = Q(audience=Post.Audience.PUBLIC)
            
            # Posts de promotion générale — filtrés par établissements actifs
            general_posts = Q(audience=Post.Audience.GENERAL_PROMOTION)

            if hasattr(user, 'student_profile'):
                # Uniquement les établissements que l'étudiant a activés dans son fil
                from apps.api.v1.establishments.models import StudentInstitution as _SI
                active_institution_ids = _SI.objects.filter(
                    student=user.student_profile, is_active=True
                ).values_list('institution_id', flat=True)
                general_posts &= Q(institution__id__in=active_institution_ids)
            elif hasattr(user, 'alumni_profile'):
                from apps.api.v1.establishments.models import AlumniInstitution as _AI
                active_ai = _AI.objects.filter(
                    alumni=user.alumni_profile, is_active=True
                ).values_list('institution_id', flat=True)
                if active_ai.exists():
                    general_posts &= Q(institution__id__in=active_ai)
                elif user.alumni_profile.institution:
                    # Fallback: FK directe si aucun enregistrement AlumniInstitution
                    general_posts &= Q(institution=user.alumni_profile.institution)
            elif hasattr(user, 'institution_admin_profile'):
                admin_institution = user.institution_admin_profile.institution
                if admin_institution:
                    general_posts &= Q(institution=admin_institution)

            # Posts de promotions spécifiques — uniquement des établissements actifs
            specific_posts = Q(audience=Post.Audience.SPECIFIC_PROMOTION)

            if hasattr(user, 'student_profile'):
                from apps.api.v1.establishments.models import StudentInstitution as _SI2
                active_inst_ids = _SI2.objects.filter(
                    student=user.student_profile, is_active=True
                ).values_list('institution_id', flat=True)
                user_promotions = user.student_profile.promotion_memberships.filter(
                    is_approved=True,
                    is_active=True,
                    promotion__institution_id__in=active_inst_ids,
                ).values_list('promotion_id', flat=True)
                specific_posts &= Q(promotion_targets__id__in=user_promotions)
            elif hasattr(user, 'alumni_profile'):
                user_promotions = user.alumni_profile.promotion_memberships.filter(
                    is_approved=True, is_active=True,
                ).values_list('promotion_id', flat=True)
                specific_posts &= Q(promotion_targets__id__in=user_promotions)
            elif hasattr(user, 'institution_admin_profile'):
                # L'admin voit tous les posts de promotions de son établissement
                admin_institution = user.institution_admin_profile.institution
                if admin_institution:
                    specific_posts &= Q(promotion_targets__institution=admin_institution)

            queryset = queryset.filter(public_posts | general_posts | specific_posts)
        else:
            # Utilisateur non connecté : seulement posts publics
            queryset = queryset.filter(audience=Post.Audience.PUBLIC)
        
        # Filtres optionnels
        post_type = self.request.query_params.get('post_type', None)
        institution = self.request.query_params.get('institution', None)
        promotion = self.request.query_params.get('promotion', None)
        author = self.request.query_params.get('author', None)
        search = self.request.query_params.get('search', '').strip()

        if post_type:
            queryset = queryset.filter(post_type=post_type)

        if institution:
            queryset = queryset.filter(institution_id=institution)

        if promotion:
            queryset = queryset.filter(promotion_targets__id=promotion)

        if author:
            queryset = queryset.filter(author_id=author)
            # Respecte le réglage de confidentialité "publications" du profil
            # consulté — sans ça, la liste des posts d'un profil marqué privé
            # resterait accessible en filtrant directement par ?author=.
            if str(user.id) != str(author):
                from django.contrib.auth import get_user_model
                from apps.api.v1.users.models import ProfilePrivacy
                AuthUser = get_user_model()
                try:
                    author_user = AuthUser.objects.get(pk=author)
                    privacy = ProfilePrivacy.for_user(author_user)
                    if not privacy.can_view(user if user.is_authenticated else None, "posts"):
                        queryset = queryset.none()
                except AuthUser.DoesNotExist:
                    pass

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(author__first_name__icontains=search) |
                Q(author__last_name__icontains=search) |
                Q(opportunity__enterprise__company_name__icontains=search)
            )

        # Annotations pour has_reacted/has_bookmarked — évite que
        # PostListSerializer fasse un `.filter()` par post (qui contournerait
        # le prefetch_related('reactions') et ferait 2 requêtes par ligne).
        if user.is_authenticated:
            queryset = queryset.annotate(
                my_reaction_kind=Subquery(
                    Reaction.objects.filter(post=OuterRef("pk"), user=user).values("kind")[:1]
                ),
                is_bookmarked_by_me=Exists(
                    Bookmark.objects.filter(post=OuterRef("pk"), user=user)
                ),
            )

        return queryset.distinct()
    
    def get_serializer_class(self):
        """Utilise différents serializers selon l'action"""
        if self.action == 'list':
            return PostListSerializer
        elif self.action == 'create':
            return PostCreateSerializer
        elif self.action in ('update', 'partial_update'):
            return PostUpdateSerializer
        return PostDetailSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """
        Crée un post + pièces jointes + objet imbriqué selon le post_type.
        Accepte JSON pur ou multipart/form-data (avec fichiers).

        Les fichiers sont lus directement depuis request.FILES.getlist('attachment_files')
        plutôt que via le serializer, car ListField(FileField) ne collecte pas
        les fichiers multipart envoyés sous la même clé répétée.
        """
        data = request.data

        # Capturer les dicts imbriqués AVANT validation (ignorés par PostCreateSerializer)
        def _parse_nested(key):
            v = data.get(key) if isinstance(data, dict) else None
            if isinstance(v, str):
                import json as _json
                try:
                    return _json.loads(v)
                except Exception:
                    return None
            return v

        opportunity_data = _parse_nested('opportunity')
        event_data       = _parse_nested('event')
        project_data     = _parse_nested('project')

        # Institution déduite du profil de l'auteur (non transmise par le client)
        institution = _get_user_institution(request.user)

        # Validation et sauvegarde du post
        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            logger.error("[PostCreate] user=%s data=%s errors=%s",
                         request.user.pk, dict(data), serializer.errors)
            raise ValidationError(serializer.errors)
        post = serializer.save(institution=institution)

        # ── Pièces jointes ─────────────────────────────────────────────────
        MAX_SIZE_MB = 20
        MAX_FILES = 10
        ALLOWED_TYPES = {
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'video/mp4', 'video/quicktime', 'video/webm',
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        }
        files = request.FILES.getlist('attachment_files')
        if len(files) > MAX_FILES:
            post.delete()
            return Response({'detail': f'Maximum {MAX_FILES} fichiers autorisés.'}, status=status.HTTP_400_BAD_REQUEST)

        for f in files:
            if f.size > MAX_SIZE_MB * 1024 * 1024:
                post.delete()
                return Response({'detail': f'Fichier "{f.name}" dépasse la taille maximale de {MAX_SIZE_MB} Mo.'}, status=status.HTTP_400_BAD_REQUEST)
            mime = getattr(f, 'content_type', '')
            if mime not in ALLOWED_TYPES:
                post.delete()
                return Response({'detail': f'Type de fichier non autorisé : {mime}.'}, status=status.HTTP_400_BAD_REQUEST)

        for idx, f in enumerate(files):
            mime = getattr(f, 'content_type', '')
            if mime.startswith('image/'):
                kind = PostAttachment.Kind.IMAGE
            elif mime.startswith('video/'):
                kind = PostAttachment.Kind.VIDEO
            else:
                kind = PostAttachment.Kind.FILE
            PostAttachment.objects.create(post=post, file=f, kind=kind, order=idx)

        # ── Objet imbriqué ─────────────────────────────────────────────────
        post_type = post.post_type
        if post_type == Post.PostType.OPPORTUNITY and opportunity_data:
            _create_nested(Opportunity, post, opportunity_data)
        elif post_type == Post.PostType.EVENT and event_data:
            _create_nested(Event, post, event_data)
        elif post_type == Post.PostType.PROJECT and project_data:
            _create_nested(Project, post, project_data)

        if request.user.role == 'enterprise' and not post.is_draft:
            company = getattr(request.user, 'enterprise_profile', None)
            if company is None:
                raise PermissionDenied("Profil Entreprise requis.")
            consume_enterprise_publication(company, post)

        headers = self.get_success_headers(serializer.data)
        out = PostListSerializer(post, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED, headers=headers)

    def retrieve(self, request, *args, **kwargs):
        """Incrémente les vues lors de la consultation"""
        instance = self.get_object()
        
        # Incrémenter les vues (sauf pour l'auteur)
        if request.user != instance.author:
            instance.views_count = F('views_count') + 1
            instance.save(update_fields=['views_count'])
            instance.refresh_from_db()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        """Met à jour un post + objets imbriqués (opportunity/event/project)."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        if instance.author != request.user:
            raise PermissionDenied("Vous ne pouvez modifier que vos propres publications.")
        was_draft = instance.is_draft

        def _parse_nested(key):
            v = request.data.get(key) if isinstance(request.data, dict) else None
            if isinstance(v, str):
                import json as _json
                try:
                    return _json.loads(v)
                except Exception:
                    return None
            return v

        opportunity_data = _parse_nested('opportunity')
        event_data       = _parse_nested('event')
        project_data     = _parse_nested('project')

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        post = serializer.save()

        # Mise à jour des pièces jointes ajoutées
        for idx, f in enumerate(request.FILES.getlist('attachment_files')):
            mime = getattr(f, 'content_type', '')
            if mime.startswith('image/'):
                kind = PostAttachment.Kind.IMAGE
            elif mime.startswith('video/'):
                kind = PostAttachment.Kind.VIDEO
            else:
                kind = PostAttachment.Kind.FILE
            PostAttachment.objects.create(post=post, file=f, kind=kind, order=idx)

        # Suppression de pièces jointes demandées.
        # Accepte à la fois les clés répétées (multipart direct) et les clés
        # indexées générées par Flutter : delete_attachment_ids[0]=1, …
        delete_ids = []
        if hasattr(request.data, 'getlist'):
            raw = request.data.getlist('delete_attachment_ids')
            if raw:
                delete_ids = raw
            else:
                i = 0
                while True:
                    v = request.data.get(f'delete_attachment_ids[{i}]')
                    if v is None:
                        break
                    delete_ids.append(v)
                    i += 1
        else:
            raw = request.data.get('delete_attachment_ids', [])
            delete_ids = raw if isinstance(raw, list) else ([raw] if raw else [])
        if delete_ids:
            PostAttachment.objects.filter(post=post, id__in=delete_ids).delete()

        # Mise à jour de l'objet imbriqué
        post_type = post.post_type
        if post_type == Post.PostType.OPPORTUNITY and opportunity_data:
            Opportunity.objects.filter(post=post).delete()
            _create_nested(Opportunity, post, opportunity_data)
        elif post_type == Post.PostType.EVENT and event_data:
            Event.objects.filter(post=post).delete()
            _create_nested(Event, post, event_data)
        elif post_type == Post.PostType.PROJECT and project_data:
            Project.objects.filter(post=post).delete()
            _create_nested(Project, post, project_data)

        if request.user.role == 'enterprise' and was_draft and not post.is_draft:
            company = getattr(request.user, 'enterprise_profile', None)
            if company is None:
                raise PermissionDenied("Profil Entreprise requis.")
            consume_enterprise_publication(company, post)

        out = PostDetailSerializer(post, context={'request': request})
        return Response(out.data)

    def perform_destroy(self, instance):
        """Archiver plutôt que supprimer"""
        if instance.author != self.request.user:
            raise PermissionDenied("Vous ne pouvez supprimer que vos propres publications.")
        instance.is_archived = True
        instance.save()
    
    @action(detail=False, methods=['get'])
    def feed(self, request):
        """
        Feed personnalisé pour l'utilisateur
        Algorithme simple : posts récents + engagement
        """
        queryset = self.get_queryset().annotate(
            engagement_score=F('reactions_count') + F('comments_count') * 2 + F('shares_count') * 3
        ).order_by('-is_pinned', '-engagement_score', '-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_posts(self, request):
        """Mes publications publiées (sans brouillons ni archives)"""
        queryset = Post.objects.filter(
            author=request.user,
            is_archived=False,
            is_draft=False,
        ).select_related(
            'author', 'institution',
            'opportunity', 'opportunity__enterprise', 'event', 'project'
        ).prefetch_related(
            'attachments', 'promotion_targets', 'reactions', 'comments'
        ).order_by('-created_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def drafts(self, request):
        """Mes brouillons"""
        queryset = Post.objects.filter(
            author=request.user,
            is_draft=True,
            is_archived=False,
        ).select_related(
            'author', 'institution',
            'opportunity', 'opportunity__enterprise', 'event', 'project'
        ).prefetch_related('attachments', 'promotion_targets').order_by('-updated_at')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PostListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = PostListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def bookmarked(self, request):
        """Publications sauvegardées — filtrables via ?search="""
        search = request.query_params.get('search', '').strip().lower()

        bookmarks = Bookmark.objects.filter(
            user=request.user
        ).select_related(
            'post', 'post__author',
            'post__opportunity', 'post__opportunity__enterprise',
            'post__event', 'post__project'
        ).prefetch_related(
            'post__attachments', 'post__promotion_targets',
            'post__reactions', 'post__comments'
        ).order_by('-created_at')

        posts = [b.post for b in bookmarks]

        if search:
            posts = [
                p for p in posts
                if search in p.title.lower()
                or search in p.content.lower()
                or search in (p.author.get_full_name() or '').lower()
                or search in getattr(getattr(p, 'opportunity', None), 'enterprise_name', '') .lower()
            ]

        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Publications tendances (dernières 7 jours)"""
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        
        queryset = self.get_queryset().filter(
            created_at__gte=seven_days_ago
        ).annotate(
            engagement_score=F('reactions_count') + F('comments_count') * 2 + F('shares_count') * 3
        ).order_by('-engagement_score')[:20]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """Réagir à un post"""
        post = self.get_object()
        reaction_kind = request.data.get('kind', 'like')
        
        # Créer ou mettre à jour la réaction
        reaction, created = Reaction.objects.update_or_create(
            user=request.user,
            post=post,
            defaults={'kind': reaction_kind}
        )
        
        # Mettre à jour le compteur
        if created:
            post.reactions_count = F('reactions_count') + 1
            post.save(update_fields=['reactions_count'])
        
        serializer = ReactionSerializer(reaction, context={'request': request})
        
        return Response({
            'status': 'réaction ajoutée' if created else 'réaction mise à jour',
            'reaction': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def unreact(self, request, pk=None):
        """Retirer une réaction"""
        post = self.get_object()
        
        deleted_count, _ = Reaction.objects.filter(
            user=request.user,
            post=post
        ).delete()
        
        if deleted_count > 0:
            post.reactions_count = F('reactions_count') - 1
            post.save(update_fields=['reactions_count'])
            return Response({'status': 'réaction retirée'})
        
        return Response(
            {'error': 'Aucune réaction trouvée'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @action(detail=True, methods=['post'])
    def bookmark(self, request, pk=None):
        """Sauvegarder un post"""
        post = self.get_object()
        
        bookmark, created = Bookmark.objects.get_or_create(
            user=request.user,
            post=post
        )
        
        if created:
            return Response({'status': 'post sauvegardé'})
        
        return Response(
            {'error': 'Post déjà sauvegardé'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def unbookmark(self, request, pk=None):
        """Retirer une sauvegarde"""
        post = self.get_object()
        
        deleted_count, _ = Bookmark.objects.filter(
            user=request.user,
            post=post
        ).delete()
        
        if deleted_count > 0:
            return Response({'status': 'sauvegarde retirée'})
        
        return Response(
            {'error': 'Aucune sauvegarde trouvée'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Partager un post"""
        post = self.get_object()
        comment = request.data.get('comment', '')
        
        share = Share.objects.create(
            user=request.user,
            original=post,
            comment=comment
        )
        
        # Mettre à jour le compteur
        post.shares_count = F('shares_count') + 1
        post.save(update_fields=['shares_count'])
        
        return Response({
            'status': 'post partagé',
            'share_id': share.id
        })
    
    @action(detail=True, methods=['get'])
    def likers(self, request, pk=None):
        """Retourne la liste des utilisateurs ayant réagi au post."""
        post = self.get_object()
        reactions = post.reactions.select_related('user').order_by('-created_at')

        def _photo(user):
            for attr in ('student_profile', 'alumni_profile', 'institution_admin_profile'):
                profile = getattr(user, attr, None)
                if profile and getattr(profile, 'photo', None):
                    try:
                        return request.build_absolute_uri(profile.photo.url)
                    except Exception:
                        pass
            return None

        data = [
            {
                'id': r.user.id,
                'full_name': r.user.get_full_name() or r.user.username,
                'photo_url': _photo(r.user),
                'kind': r.kind,
            }
            for r in reactions
        ]
        return Response(data)

    @action(detail=True, methods=['post'])
    def pin(self, request, pk=None):
        """Épingler un post (admin établissement ou auteur)"""
        post = self.get_object()
        
        # Vérifier les permissions
        can_pin = (
            post.author == request.user or
            (hasattr(request.user, 'institution_admin_profile') and 
             post.institution == request.user.institution_admin_profile.institution)
        )
        
        if not can_pin:
            return Response(
                {'error': 'Permission refusée'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        post.is_pinned = True
        post.save(update_fields=['is_pinned'])
        
        return Response({'status': 'post épinglé'})
    
    @action(detail=True, methods=['post'])
    def unpin(self, request, pk=None):
        """Désépingler un post"""
        post = self.get_object()
        
        # Vérifier les permissions
        can_unpin = (
            post.author == request.user or
            (hasattr(request.user, 'institution_admin_profile') and 
             post.institution == request.user.institution_admin_profile.institution)
        )
        
        if not can_unpin:
            return Response(
                {'error': 'Permission refusée'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        post.is_pinned = False
        post.save(update_fields=['is_pinned'])
        
        return Response({'status': 'post désépinglé'})


# ==================== OPPORTUNITY VIEWSET ====================

class OpportunityViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les opportunités
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = GenerousResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['post__title', 'post__content', 'location_city', 'location_country']
    filterset_fields = ['category', 'status', 'work_mode', 'contract_type']
    ordering_fields = ['post__created_at', 'deadline']
    ordering = ['-post__created_at']
    
    def get_queryset(self):
        """Retourne les opportunités visibles — mêmes règles que
        PostViewSet (voir `visible_post_filter`)."""
        queryset = Opportunity.objects.select_related(
            'post', 'post__author', 'enterprise'
        ).filter(
            post__is_archived=False
        ).filter(
            visible_post_filter(self.request.user, prefix='post__')
        ).distinct()

        # Filtres supplémentaires
        show_closed = self.request.query_params.get('show_closed', 'false').lower() == 'true'
        if not show_closed:
            queryset = queryset.filter(status=Opportunity.Status.OPEN)

        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return OpportunityCreateSerializer
        return OpportunitySerializer
    
    @action(detail=False, methods=['get'])
    def recommended(self, request):
        """Opportunités recommandées pour l'utilisateur"""
        # TODO: Implémenter algorithme de recommandation
        # Pour l'instant, retourne les opportunités récentes
        
        queryset = self.get_queryset().filter(
            status=Opportunity.Status.OPEN
        ).order_by('-post__created_at')[:10]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def apply(self, request, pk=None):
        """Postuler à une opportunité"""
        opportunity = self.get_object()
        
        # Vérifier si déjà postulé
        if Application.objects.filter(user=request.user, opportunity=opportunity).exists():
            return Response(
                {'error': 'Vous avez déjà postulé à cette opportunité'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer la candidature
        application = Application.objects.create(
            user=request.user,
            opportunity=opportunity,
            resume=request.data.get('resume'),
            cover_letter=request.data.get('cover_letter', ''),
            portfolio_url=request.data.get('portfolio_url', '')
        )
        
        serializer = ApplicationSerializer(application, context={'request': request})
        
        return Response({
            'status': 'candidature soumise',
            'application': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Fermer une opportunité (auteur uniquement)"""
        opportunity = self.get_object()
        
        if opportunity.post.author != request.user:
            return Response(
                {'error': 'Permission refusée'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        opportunity.status = Opportunity.Status.CLOSED
        opportunity.save()
        
        return Response({'status': 'opportunité fermée'})
    
    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """Rouvrir une opportunité (auteur uniquement)"""
        opportunity = self.get_object()
        
        if opportunity.post.author != request.user:
            return Response(
                {'error': 'Permission refusée'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        opportunity.status = Opportunity.Status.OPEN
        opportunity.save()
        
        return Response({'status': 'opportunité rouverte'})
    
    @action(detail=True, methods=['get'])
    def applications(self, request, pk=None):
        """Liste des candidatures (auteur uniquement)"""
        opportunity = self.get_object()
        
        if opportunity.post.author != request.user:
            return Response(
                {'error': 'Permission refusée'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        applications = opportunity.applications.select_related('user').order_by('-created_at')
        serializer = ApplicationSerializer(applications, many=True, context={'request': request})
        
        return Response(serializer.data)


# ==================== EVENT VIEWSET ====================

class EventViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les événements
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = GenerousResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['is_online']
    ordering_fields = ['starts_at']
    ordering = ['starts_at']
    
    def get_queryset(self):
        """Retourne les événements visibles — mêmes règles que PostViewSet
        (voir `visible_post_filter`), pour ne pas exposer les événements
        ciblant une promotion/établissement à des utilisateurs hors périmètre."""
        return Event.objects.select_related(
            'post', 'post__author'
        ).filter(
            post__is_archived=False
        ).filter(
            visible_post_filter(self.request.user, prefix='post__')
        ).distinct()
    
    def get_serializer_class(self):
        return EventSerializer
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Événements à venir"""
        now = timezone.now()
        
        queryset = self.get_queryset().filter(
            starts_at__gte=now
        ).order_by('starts_at')[:20]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_events(self, request):
        """Événements auxquels je participe"""
        rsvps = RSVP.objects.filter(
            user=request.user,
            status=RSVP.Status.GOING
        ).select_related('event').order_by('event__starts_at')

        events = [rsvp.event for rsvp in rsvps]
        serializer = self.get_serializer(events, many=True)

        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def calendar(self, request):
        """
        GET /posts/events/calendar/?start=YYYY-MM-DD&end=YYYY-MM-DD
        Agrège les événements visibles sur une plage de dates (vue mois/semaine
        du calendrier), groupés par jour (clé ISO `YYYY-MM-DD`). Par défaut :
        du début du mois courant à la fin du mois suivant.
        """
        start_raw = request.query_params.get('start')
        end_raw = request.query_params.get('end')

        today = timezone.localdate()
        if start_raw:
            try:
                start_date = datetime.date.fromisoformat(start_raw)
            except ValueError:
                return Response({'error': "Paramètre 'start' invalide (attendu AAAA-MM-JJ)."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            start_date = today.replace(day=1)

        if end_raw:
            try:
                end_date = datetime.date.fromisoformat(end_raw)
            except ValueError:
                return Response({'error': "Paramètre 'end' invalide (attendu AAAA-MM-JJ)."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            next_month = (start_date.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            end_date = (next_month.replace(day=28) + datetime.timedelta(days=4)).replace(day=1) - datetime.timedelta(days=1)

        if end_date < start_date:
            return Response({'error': "'end' doit être postérieur ou égal à 'start'."}, status=status.HTTP_400_BAD_REQUEST)

        range_start = timezone.make_aware(datetime.datetime.combine(start_date, datetime.time.min))
        range_end = timezone.make_aware(datetime.datetime.combine(end_date, datetime.time.max))

        events = self.get_queryset().filter(
            starts_at__gte=range_start, starts_at__lte=range_end
        ).order_by('starts_at')

        serializer = self.get_serializer(events, many=True, context=self.get_serializer_context())

        by_day = {}
        for event_data, event in zip(serializer.data, events):
            key = timezone.localtime(event.starts_at).date().isoformat()
            by_day.setdefault(key, []).append(event_data)

        return Response({
            'start': start_date.isoformat(),
            'end': end_date.isoformat(),
            'days': by_day,
        })

    @action(detail=True, methods=['post'])
    def rsvp(self, request, pk=None):
        """Répondre à un événement (RSVP)"""
        event = self.get_object()
        rsvp_status = request.data.get('status', RSVP.Status.GOING)
        
        # Vérifier la capacité
        if rsvp_status == RSVP.Status.GOING and event.is_full:
            return Response(
                {'error': 'L\'événement est complet'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Créer ou mettre à jour le RSVP
        rsvp, created = RSVP.objects.update_or_create(
            user=request.user,
            event=event,
            defaults={'status': rsvp_status}
        )
        
        serializer = RSVPSerializer(rsvp, context={'request': request})
        
        return Response({
            'status': 'RSVP enregistré',
            'rsvp': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def attendees(self, request, pk=None):
        """Liste des participants"""
        event = self.get_object()
        
        rsvps = event.rsvps.filter(
            status=RSVP.Status.GOING
        ).select_related('user').order_by('-created_at')
        
        serializer = RSVPSerializer(rsvps, many=True, context={'request': request})
        return Response(serializer.data)


# ==================== PROJECT VIEWSET ====================

class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les projets
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = GenerousResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'looking_for_members']
    ordering = ['-post__created_at']
    
    def get_queryset(self):
        """Retourne les projets visibles — mêmes règles que PostViewSet
        (voir `visible_post_filter`)."""
        return Project.objects.select_related(
            'post', 'post__author'
        ).prefetch_related('team').filter(
            post__is_archived=False
        ).filter(
            visible_post_filter(self.request.user, prefix='post__')
        ).distinct()
    
    def get_serializer_class(self):
        return ProjectSerializer
    
    @action(detail=False, methods=['get'])
    def looking_for_members(self, request):
        """Projets qui recrutent"""
        queryset = self.get_queryset().filter(
            looking_for_members=True,
            status=Project.Status.ACTIVE
        )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Rejoindre l'équipe"""
        project = self.get_object()
        
        if not project.looking_for_members:
            return Response(
                {'error': 'Ce projet ne recrute pas actuellement'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if request.user in project.team.all():
            return Response(
                {'error': 'Vous faites déjà partie de l\'équipe'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        project.team.add(request.user)
        
        return Response({'status': 'vous avez rejoint l\'équipe'})
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Quitter l'équipe"""
        project = self.get_object()
        
        if request.user not in project.team.all():
            return Response(
                {'error': 'Vous ne faites pas partie de l\'équipe'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        project.team.remove(request.user)
        
        return Response({'status': 'vous avez quitté l\'équipe'})


# ==================== APPLICATION VIEWSET ====================

class ApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les candidatures
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = GenerousResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'opportunity']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Retourne les candidatures de l'utilisateur ou les candidatures reçues"""
        if getattr(self, 'swagger_fake_view', False):
            return Application.objects.none()

        user = self.request.user

        # Candidatures soumises par l'utilisateur
        my_applications = Q(user=user)
        
        # Candidatures reçues (si auteur de l'opportunité)
        received_applications = Q(opportunity__post__author=user)
        
        return Application.objects.filter(
            my_applications | received_applications
        ).select_related('user', 'opportunity', 'opportunity__post').distinct()
    
    def get_serializer_class(self):
        return ApplicationSerializer
    
    @action(detail=False, methods=['get'])
    def my_applications(self, request):
        """Mes candidatures"""
        queryset = Application.objects.filter(
            user=request.user
        ).select_related('opportunity', 'opportunity__post').order_by('-created_at')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Changer le statut (recruteur uniquement)"""
        application = self.get_object()
        
        # Vérifier que l'utilisateur est l'auteur de l'opportunité
        if application.opportunity.post.author != request.user:
            return Response(
                {'error': 'Permission refusée'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_status = request.data.get('status')
        
        if new_status not in dict(Application.STATUS).keys():
            return Response(
                {'error': 'Statut invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        application.status = new_status
        application.save()
        
        serializer = self.get_serializer(application)
        
        return Response({
            'status': 'statut mis à jour',
            'application': serializer.data
        })


# ==================== COMMENT VIEWSET ====================

class CommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les commentaires
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = GenerousResultsSetPagination
    filter_backends = [filters.OrderingFilter]
    ordering = ['created_at']
    
    def get_queryset(self):
        """Retourne les commentaires d'un post. Le paramètre ?post= est obligatoire en liste."""
        if getattr(self, 'swagger_fake_view', False):
            return Comment.objects.none()
        post_id = self.request.query_params.get('post')
        if not post_id and self.action == 'list':
            return Comment.objects.none()
        queryset = Comment.objects.select_related('user', 'post').prefetch_related(
            Prefetch('replies', queryset=Comment.objects.select_related('user'))
        )
        if post_id:
            queryset = queryset.filter(post_id=post_id, parent__isnull=True)
        return queryset
    
    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return CommentCreateSerializer
        return CommentSerializer

    def perform_create(self, serializer):
        """Auto-assign user et incrémenter compteur"""
        comment = serializer.save(user=self.request.user)
        
        # Incrémenter le compteur de commentaires du post
        comment.post.comments_count = F('comments_count') + 1
        comment.post.save(update_fields=['comments_count'])
    
    def perform_update(self, serializer):
        """Vérifier permissions et marquer comme édité"""
        if serializer.instance.user != self.request.user:
            raise PermissionDenied("Vous ne pouvez modifier que vos propres commentaires.")
        
        serializer.save(is_edited=True)
    
    def perform_destroy(self, instance):
        """Vérifier permissions et décrémenter compteur"""
        if instance.user != self.request.user:
            raise PermissionDenied("Vous ne pouvez supprimer que vos propres commentaires.")
        
        # Décrémenter le compteur
        instance.post.comments_count = F('comments_count') - 1
        instance.post.save(update_fields=['comments_count'])
        
        instance.delete()
    
    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):
        """Récupérer les réponses à un commentaire"""
        comment = self.get_object()
        replies = comment.replies.select_related('user').order_by('created_at')

        serializer = self.get_serializer(replies, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """Liker un commentaire (toggle). Retourne le nouvel état."""
        comment = self.get_object()
        like, created = CommentLike.objects.get_or_create(comment=comment, user=request.user)
        if not created:
            like.delete()
        likes_count = comment.likes.count()
        return Response({
            'liked': created,
            'likes_count': likes_count,
        })

    @action(detail=True, methods=['post'])
    def unreact(self, request, pk=None):
        """Retirer le like d'un commentaire."""
        comment = self.get_object()
        deleted, _ = CommentLike.objects.filter(comment=comment, user=request.user).delete()
        return Response({
            'liked': False,
            'likes_count': comment.likes.count(),
        })


# ==================== REACTION VIEWSET ====================

class ReactionViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les réactions
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = GenerousResultsSetPagination
    http_method_names = ['get', 'post', 'delete']
    
    def get_queryset(self):
        """Retourne les réactions d'un post. Le paramètre ?post= est obligatoire en liste."""
        if getattr(self, 'swagger_fake_view', False):
            return Reaction.objects.none()
        post_id = self.request.query_params.get('post')
        if not post_id and self.action == 'list':
            return Reaction.objects.none()
        queryset = Reaction.objects.select_related('user', 'post')
        if post_id:
            queryset = queryset.filter(post_id=post_id)
        return queryset
    
    def get_serializer_class(self):
        return ReactionSerializer


# ==================== RSVP VIEWSET ====================

class RSVPViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les RSVP
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = GenerousResultsSetPagination
    
    def get_queryset(self):
        """Retourne les RSVP de l'utilisateur"""
        if getattr(self, 'swagger_fake_view', False):
            return RSVP.objects.none()

        return RSVP.objects.filter(
            user=self.request.user
        ).select_related('event', 'event__post')
    
    def get_serializer_class(self):
        return RSVPSerializer
    
    @action(detail=False, methods=['get'])
    def my_rsvps(self, request):
        """Mes réponses aux événements"""
        queryset = self.get_queryset().order_by('event__starts_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# ==================== BOOKMARK VIEWSET ====================

class BookmarkViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les sauvegardes
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = GenerousResultsSetPagination
    http_method_names = ['get', 'post', 'delete']
    
    def get_queryset(self):
        """Retourne les sauvegardes de l'utilisateur"""
        if getattr(self, 'swagger_fake_view', False):
            return Bookmark.objects.none()

        return Bookmark.objects.filter(
            user=self.request.user
        ).select_related('post', 'post__author').order_by('-created_at')
    
    def get_serializer_class(self):
        return BookmarkSerializer
    
    def perform_create(self, serializer):
        """Auto-assign user"""
        serializer.save(user=self.request.user)
