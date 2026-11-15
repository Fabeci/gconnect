"""
G-Connect - Posts Serializers (COMPLETS)
Serializers pour l'application des publications avec toutes les fonctionnalités
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Count, Q

from apps.api.v1.posts.models import (
    Post, PostAttachment, Opportunity, Event, Project,
    Reaction, Comment, CommentLike, Share, Bookmark, Application, RSVP
)
from apps.api.v1.establishments.models import Promotion

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les informations utilisateur"""
    full_name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    role_display = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        ref_name = "PostUserBasic"
        fields = ['id', 'username', 'full_name', 'email', 'photo_url', 'role', 'role_display']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_photo_url(self, obj):
        request = self.context.get('request')
        if obj.photo:
            return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url
        return None
    
    def get_role_display(self, obj):
        """Rôle avec emoji"""
        role_badges = {
            'student': {'emoji': '👨‍🎓', 'label': 'Étudiant'},
            'alumni': {'emoji': '🎓', 'label': 'Alumni'},
            'etablissement': {'emoji': '🏛️', 'label': 'Admin Établissement'},
            'enterprise': {'emoji': '🏢', 'label': 'Entreprise'},
            'superAdmin': {'emoji': '⚡', 'label': 'Super Admin'}
        }
        return role_badges.get(obj.role, {'emoji': '👤', 'label': 'Utilisateur'})


# ==================== POST ATTACHMENT SERIALIZERS ====================

class PostAttachmentSerializer(serializers.ModelSerializer):
    """Serializer pour les pièces jointes — retourne l'URL absolue du fichier"""
 
    # file_url retourne l'URL complète avec domaine (ex: https://backend.gconnectapp.com/media/...)
    # Nécessaire pour Flutter qui ne peut pas construire l'URL relative seul
    file_url = serializers.SerializerMethodField()
 
    class Meta:
        model = PostAttachment
        fields = ['id', 'file', 'file_url', 'kind', 'alt_text', 'order']
 
    def get_file_url(self, obj):
        request = self.context.get('request')
        if not obj.file:
            return None
        if request:
            # build_absolute_uri donne https://backend.gconnectapp.com/media/posts/xxx.jpg
            return request.build_absolute_uri(obj.file.url)
        # Fallback sans request
        return f"https://backend.gconnectapp.com{obj.file.url}"

# ==================== POST SERIALIZERS ====================

class PostTypeDetailsMixin:
    """
    Résout les relations OneToOne optionnelles d'un Post (opportunity/event/project)
    selon son post_type. Partagé entre PostListSerializer et PostDetailSerializer
    pour garantir que le feed et le détail exposent exactement les mêmes données
    spécifiques au type — pas de divergence entre les deux vues.
    """

    def get_opportunity(self, obj):
        """Détails opportunité si applicable"""
        if obj.post_type == 'opportunity' and hasattr(obj, 'opportunity'):
            from .serializers import OpportunitySerializer
            return OpportunitySerializer(obj.opportunity, context=self.context).data
        return None

    def get_event(self, obj):
        """Détails événement si applicable"""
        if obj.post_type == 'event' and hasattr(obj, 'event'):
            from .serializers import EventSerializer
            return EventSerializer(obj.event, context=self.context).data
        return None

    def get_project(self, obj):
        """Détails projet si applicable"""
        if obj.post_type == 'project' and hasattr(obj, 'project'):
            from .serializers import ProjectSerializer
            return ProjectSerializer(obj.project, context=self.context).data
        return None


class PostListSerializer(PostTypeDetailsMixin, serializers.ModelSerializer):
    """Serializer pour la liste des posts (feed)"""
    author = UserBasicSerializer(read_only=True)
    institution_name = serializers.CharField(source='institution.name', read_only=True)
    post_type_display = serializers.SerializerMethodField()
    audience_display = serializers.SerializerMethodField()
    attachments_preview = serializers.SerializerMethodField()
    engagement_summary = serializers.SerializerMethodField()
    has_reacted = serializers.SerializerMethodField()
    has_bookmarked = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    # Relations OneToOne optionnelles (mêmes données que le détail, cf. PostTypeDetailsMixin)
    opportunity = serializers.SerializerMethodField()
    event = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'institution_name', 'title', 'content',
            'post_type', 'post_type_display', 'audience', 'audience_display',
            'attachments_preview', 'engagement_summary', 'has_reacted',
            'has_bookmarked', 'is_pinned', 'is_archived', 'is_draft', 'can_edit',
            'created_at', 'updated_at', 'opportunity', 'event', 'project'
        ]
    
    def get_post_type_display(self, obj):
        """Type avec emoji et couleur"""
        types = {
            'opportunity': {'emoji': '💼', 'label': 'Opportunité', 'color': '#28a745'},
            'event': {'emoji': '📅', 'label': 'Événement', 'color': '#007bff'},
            'project': {'emoji': '🚀', 'label': 'Projet', 'color': '#6f42c1'},
            'discussion': {'emoji': '💬', 'label': 'Discussion', 'color': '#6c757d'},
            'share': {'emoji': '🔄', 'label': 'Partage', 'color': '#17a2b8'},
        }
        return types.get(obj.post_type, {'emoji': '📝', 'label': 'Publication', 'color': '#000'})
    
    def get_audience_display(self, obj):
        """Audience avec emoji"""
        audiences = {
            'public': {
                'emoji': '🌍',
                'label': 'Public',
                'description': 'Visible par tout le monde'
            },
            'general_promotion': {
                'emoji': '🏛️',
                'label': 'Promotion générale',
                'description': f"Membres de l'etablissement" if not obj.institution else f"Membres de {obj.institution.name}"
            },
            'specific_promotion': {
                'emoji': '🎯',
                'label': 'Promotion(s) spécifique(s)',
                'description': f'{obj.promotion_targets.count()} promotion(s) ciblée(s)'
            }
        }
        return audiences.get(obj.audience, audiences['public'])
    
    def get_attachments_preview(self, obj):
        """Aperçu des pièces jointes — `len()` sur une relation déjà
        prefetch_related (au lieu de `.count()`, qui contournerait le cache
        et refait une requête par post)."""
        attachments = list(obj.attachments.all())[:3]
        return {
            'count': len(obj.attachments.all()),
            'preview': PostAttachmentSerializer(attachments, many=True, context=self.context).data
        }

    def get_engagement_summary(self, obj):
        """Résumé de l'engagement"""
        return {
            'views': obj.views_count,
            'reactions': obj.reactions_count,
            'comments': obj.comments_count,
            'shares': obj.shares_count
        }

    def get_has_reacted(self, obj):
        """Vérifie si l'utilisateur a réagi — lit l'annotation
        `my_reaction_kind` posée par PostViewSet.get_queryset() (Subquery)
        plutôt que `.filter()` sur `reactions`, qui contournerait le
        prefetch_related et ferait une requête par post."""
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False

        kind = getattr(obj, 'my_reaction_kind', None)
        if kind:
            return {'has_reacted': True, 'reaction_type': kind}
        return {'has_reacted': False}

    def get_has_bookmarked(self, obj):
        """Vérifie si l'utilisateur a sauvegardé — lit l'annotation
        `is_bookmarked_by_me` (Exists) posée par get_queryset()."""
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False

        return bool(getattr(obj, 'is_bookmarked_by_me', False))
    
    def get_can_edit(self, obj):
        """Vérifie si l'utilisateur peut éditer"""
        request = self.context.get('request')
        if not request or not request.user:
            return False
        
        return obj.author == request.user


class PostDetailSerializer(PostTypeDetailsMixin, serializers.ModelSerializer):
    """Serializer détaillé pour un post"""
    author = UserBasicSerializer(read_only=True)
    institution = serializers.SerializerMethodField()
    post_type_display = serializers.SerializerMethodField()
    audience_display = serializers.SerializerMethodField()
    promotion_targets_list = serializers.SerializerMethodField()
    attachments = PostAttachmentSerializer(many=True, read_only=True)
    reactions_summary = serializers.SerializerMethodField()
    top_comments = serializers.SerializerMethodField()
    engagement_stats = serializers.SerializerMethodField()
    has_reacted = serializers.SerializerMethodField()
    has_bookmarked = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    
    # Relations OneToOne optionnelles
    opportunity = serializers.SerializerMethodField()
    event = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    
    class Meta:
        model = Post
        fields = [
            'id', 'author', 'institution', 'title', 'content',
            'post_type', 'post_type_display', 'audience', 'audience_display',
            'promotion_targets_list', 'attachments', 'reactions_summary',
            'top_comments', 'engagement_stats', 'has_reacted', 'has_bookmarked',
            'is_pinned', 'is_archived', 'is_draft', 'can_edit', 'created_at', 'updated_at',
            'opportunity', 'event', 'project'
        ]
    
    def get_post_type_display(self, obj):
        """Type avec emoji et couleur"""
        types = {
            'opportunity': {'emoji': '💼', 'label': 'Opportunité', 'color': '#28a745'},
            'event': {'emoji': '📅', 'label': 'Événement', 'color': '#007bff'},
            'project': {'emoji': '🚀', 'label': 'Projet', 'color': '#6f42c1'},
            'discussion': {'emoji': '💬', 'label': 'Discussion', 'color': '#6c757d'},
            'share': {'emoji': '🔄', 'label': 'Partage', 'color': '#17a2b8'},
        }
        return types.get(obj.post_type, {'emoji': '📝', 'label': 'Publication', 'color': '#000'})
    
    def get_audience_display(self, obj):
        """Audience avec emoji"""
        audiences = {
            'public': {
                'emoji': '🌍',
                'label': 'Public',
                'description': 'Visible par tout le monde'
            },
            'general_promotion': {
                'emoji': '🏛️',
                'label': 'Promotion générale',
                'description': f"Membres de l'etablissement" if not obj.institution else f"Membres de {obj.institution.name}"
            },
            'specific_promotion': {
                'emoji': '🎯',
                'label': 'Promotion(s) spécifique(s)',
                'description': f'{obj.promotion_targets.count()} promotion(s) ciblée(s)'
            }
        }
        return audiences.get(obj.audience, audiences['public'])
    
    def get_institution(self, obj):
        """Infos établissement avec logo."""
        if not obj.institution:
            return None
        inst = obj.institution
        request = self.context.get('request')
        logo_url = None
        if inst.logo:
            logo_url = request.build_absolute_uri(inst.logo.url) if request else inst.logo.url
        cover_url = None
        if hasattr(inst, 'cover_image') and inst.cover_image:
            cover_url = request.build_absolute_uri(inst.cover_image.url) if request else inst.cover_image.url
        return {
            'id': inst.id,
            'name': inst.name,
            'acronym': getattr(inst, 'acronym', ''),
            'logo_url': logo_url,
            'cover_image_url': cover_url,
        }

    def get_promotion_targets_list(self, obj):
        """Liste des promotions cibles avec image de couverture."""
        request = self.context.get('request')
        result = []
        for p in obj.promotion_targets.select_related('institution').all():
            cover_url = None
            if p.cover_image:
                cover_url = request.build_absolute_uri(p.cover_image.url) if request else p.cover_image.url
            result.append({
                'id': p.id,
                'name': p.name,
                'institution': p.institution.name if p.institution else '',
                'cover_image_url': cover_url,
            })
        return result
    
    def get_reactions_summary(self, obj):
        """Résumé groupé des réactions"""
        reactions = obj.reactions.values('kind').annotate(count=Count('kind'))
        summary = {}
        
        for reaction in reactions:
            kind = reaction['kind']
            count = reaction['count']
            summary[kind] = {
                'count': count,
                'emoji': self._get_reaction_emoji(kind)
            }
        
        return summary
    
    def _get_reaction_emoji(self, kind):
        """Mapping réaction → emoji"""
        emojis = {
            'like': '👍', 'celebrate': '🎉', 'support': '💪',
            'love': '❤️', 'insightful': '💡'
        }
        return emojis.get(kind, '👍')
    
    def get_top_comments(self, obj):
        """3 premiers commentaires"""
        from .serializers import CommentSerializer  # Import local pour éviter circularité
        comments = obj.comments.filter(parent__isnull=True).order_by('-created_at')[:3]
        return CommentSerializer(comments, many=True, context=self.context).data
    
    def get_engagement_stats(self, obj):
        """Statistiques d'engagement détaillées"""
        total_engagement = obj.reactions_count + obj.comments_count + obj.shares_count
        engagement_rate = (total_engagement / obj.views_count * 100) if obj.views_count > 0 else 0
        
        return {
            'views': obj.views_count,
            'reactions': obj.reactions_count,
            'comments': obj.comments_count,
            'shares': obj.shares_count,
            'total_engagement': total_engagement,
            'engagement_rate': round(engagement_rate, 2)
        }
    
    def get_has_reacted(self, obj):
        """Vérifie la réaction de l'utilisateur"""
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        
        reaction = obj.reactions.filter(user=request.user).first()
        if reaction:
            return {
                'has_reacted': True,
                'reaction_type': reaction.kind
            }
        return {'has_reacted': False}
    
    def get_has_bookmarked(self, obj):
        """Vérifie la sauvegarde"""
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        
        return obj.bookmarked_by.filter(user=request.user).exists()
    
    def get_can_edit(self, obj):
        """Permissions d'édition"""
        request = self.context.get('request')
        if not request or not request.user:
            return False

        return obj.author == request.user


class PostCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer un post.

    Les fichiers joints (attachment_files) et l'institution sont gérés
    directement dans PostViewSet.create() pour contourner la limitation
    de ListField avec les uploads multipart répétés (même clé).
    """

    class Meta:
        model = Post
        fields = ['title', 'content', 'post_type', 'audience', 'promotion_targets', 'is_draft']

    def validate(self, data):
        audience = data.get('audience')
        promotion_targets = data.get('promotion_targets', [])
        is_draft = data.get('is_draft', False)

        if not is_draft and audience == Post.Audience.SPECIFIC_PROMOTION and not promotion_targets:
            raise serializers.ValidationError({
                'promotion_targets': "Au moins une promotion est requise pour cette audience."
            })

        return data

    def create(self, validated_data):
        promotion_targets = validated_data.pop('promotion_targets', [])
        request = self.context.get('request')

        post = Post.objects.create(author=request.user, **validated_data)

        if promotion_targets:
            post.promotion_targets.set(promotion_targets)

        return post


class PostUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour modifier un post existant (PATCH/PUT)."""

    class Meta:
        model = Post
        fields = ['title', 'content', 'audience', 'promotion_targets', 'is_draft']

    def validate(self, data):
        audience = data.get('audience', self.instance.audience if self.instance else None)
        promotion_targets = data.get('promotion_targets', None)

        if audience == Post.Audience.SPECIFIC_PROMOTION:
            existing = list(self.instance.promotion_targets.all()) if self.instance else []
            targets = promotion_targets if promotion_targets is not None else existing
            if not targets:
                raise serializers.ValidationError({
                    'promotion_targets': "Au moins une promotion est requise pour cette audience."
                })

        return data

    def update(self, instance, validated_data):
        promotion_targets = validated_data.pop('promotion_targets', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if promotion_targets is not None:
            instance.promotion_targets.set(promotion_targets)
        return instance


# ==================== OPPORTUNITY SERIALIZERS ====================

class OpportunitySerializer(serializers.ModelSerializer):
    """Serializer pour les opportunités"""
    post_title = serializers.CharField(source='post.title', read_only=True)
    enterprise_name = serializers.CharField(source='enterprise.company_name', read_only=True)
    category_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    location_display = serializers.SerializerMethodField()
    salary_display = serializers.SerializerMethodField()
    is_expired = serializers.ReadOnlyField()
    applications_count = serializers.SerializerMethodField()
    has_applied = serializers.SerializerMethodField()
    
    class Meta:
        model = Opportunity
        fields = [
            'id', 'post', 'post_title', 'enterprise', 'enterprise_name',
            'category', 'category_display', 'status', 'status_display',
            'location_city', 'location_country', 'location_display',
            'work_mode', 'contract_type', 'duration_months', 'start_date',
            'salary_min', 'salary_max', 'currency', 'salary_display',
            'application_url', 'application_email', 'deadline', 'is_expired',
            'instructor', 'available_spots',
            'tags', 'required_skills', 'applications_count', 'has_applied'
        ]
        read_only_fields = ['is_expired']
    
    def get_category_display(self, obj):
        """Catégorie avec emoji"""
        categories = {
            'job': {'emoji': '💼', 'label': 'Emploi', 'color': '#28a745'},
            'internship': {'emoji': '🎓', 'label': 'Stage', 'color': '#007bff'},
            'training': {'emoji': '📚', 'label': 'Formation', 'color': '#6f42c1'},
            'apprenticeship': {'emoji': '🔧', 'label': 'Alternance', 'color': '#fd7e14'},
            'volunteer': {'emoji': '❤️', 'label': 'Bénévolat', 'color': '#17a2b8'},
            'project': {'emoji': '🚀', 'label': 'Projet', 'color': '#dc3545'},
        }
        return categories.get(obj.category, {'emoji': '💼', 'label': 'Opportunité', 'color': '#000'})
    
    def get_status_display(self, obj):
        """Statut avec couleur"""
        if obj.status == 'open':
            if obj.is_expired:
                return {'status': 'open', 'label': '⚠️ Ouverte (expirée)', 'color': 'orange'}
            return {'status': 'open', 'label': '🟢 Ouverte', 'color': 'green'}
        return {'status': 'closed', 'label': '🔴 Fermée', 'color': 'red'}
    
    def get_location_display(self, obj):
        """Localisation formatée"""
        parts = []
        if obj.location_city:
            parts.append(obj.location_city)
        if obj.location_country:
            parts.append(obj.location_country)
        return ', '.join(parts) if parts else None
    
    def get_salary_display(self, obj):
        """Salaire formaté"""
        if not obj.salary_min and not obj.salary_max:
            return 'Non communiqué'
        
        currency = obj.currency or 'XOF'
        
        if obj.salary_min and obj.salary_max:
            return f"{obj.salary_min:,} - {obj.salary_max:,} {currency}"
        elif obj.salary_min:
            return f"À partir de {obj.salary_min:,} {currency}"
        elif obj.salary_max:
            return f"Jusqu'à {obj.salary_max:,} {currency}"
    
    def get_applications_count(self, obj):
        """Nombre de candidatures"""
        return obj.applications.count()
    
    def get_has_applied(self, obj):
        """Vérifie si l'utilisateur a postulé"""
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        
        return obj.applications.filter(user=request.user).exists()


class OpportunityCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer une opportunité"""
    
    class Meta:
        model = Opportunity
        fields = [
            'post', 'enterprise', 'category', 'location_city',
            'location_country', 'work_mode', 'contract_type',
            'duration_months', 'start_date', 'salary_min', 'salary_max',
            'currency', 'application_url', 'application_email',
            'deadline', 'instructor', 'available_spots',
            'tags', 'required_skills'
        ]
    
    def validate(self, data):
        """Validation selon catégorie"""
        category = data.get('category')
        
        # Stage/Alternance : durée requise
        if category in [Opportunity.Category.INTERNSHIP, Opportunity.Category.APPRENTICESHIP]:
            if not data.get('duration_months'):
                raise serializers.ValidationError({
                    'duration_months': f'La durée est requise pour un(e) {dict(Opportunity.Category.choices)[category]}'
                })
        
        # Emploi : type de contrat requis
        if category == Opportunity.Category.JOB:
            if not data.get('contract_type'):
                raise serializers.ValidationError({
                    'contract_type': 'Le type de contrat est requis pour un emploi'
                })
        
        return data


# ==================== EVENT SERIALIZERS ====================

class EventSerializer(serializers.ModelSerializer):
    """Serializer pour les événements"""
    post_title = serializers.CharField(source='post.title', read_only=True)
    cover_image_url = serializers.SerializerMethodField()
    location_display = serializers.SerializerMethodField()
    is_full = serializers.ReadOnlyField()
    attendees_count = serializers.SerializerMethodField()
    my_rsvp = serializers.SerializerMethodField()
    time_until_event = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'post', 'post_title', 'starts_at', 'ends_at',
            'is_online', 'location_name', 'address', 'city', 'country',
            'location_display', 'online_url', 'cover_image_url',
            'capacity', 'is_full', 'rsvp_deadline', 'attendees_count',
            'my_rsvp', 'time_until_event'
        ]
        read_only_fields = ['is_full']
    
    def validate_starts_at(self, value):
        from django.utils.timezone import make_aware, is_naive
        return make_aware(value) if value and is_naive(value) else value

    def validate_ends_at(self, value):
        from django.utils.timezone import make_aware, is_naive
        return make_aware(value) if value and is_naive(value) else value

    def get_cover_image_url(self, obj):
        if not obj.cover_image:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.cover_image.url) if request else obj.cover_image.url

    def get_location_display(self, obj):
        """Localisation formatée"""
        if obj.is_online:
            return '🌐 En ligne'
        
        parts = []
        if obj.location_name:
            parts.append(obj.location_name)
        if obj.city:
            parts.append(obj.city)
        return ', '.join(parts) if parts else None
    
    def get_attendees_count(self, obj):
        """Nombre de participants confirmés"""
        return obj.rsvps.filter(status=RSVP.Status.GOING).count()
    
    def get_my_rsvp(self, obj):
        """RSVP de l'utilisateur"""
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return None
        
        rsvp = obj.rsvps.filter(user=request.user).first()
        if rsvp:
            return {
                'has_rsvp': True,
                'status': rsvp.status,
                'status_label': rsvp.get_status_display()
            }
        return {'has_rsvp': False}
    
    def get_time_until_event(self, obj):
        """Temps jusqu'à l'événement"""
        from django.utils.dateparse import parse_datetime
        from django.utils.timezone import make_aware, is_naive
        now = timezone.now()

        starts_at = obj.starts_at
        if isinstance(starts_at, str):
            starts_at = parse_datetime(starts_at) or now
        if starts_at is not None and is_naive(starts_at):
            starts_at = make_aware(starts_at)

        ends_at = obj.ends_at
        if isinstance(ends_at, str):
            ends_at = parse_datetime(ends_at)
        if ends_at is not None and is_naive(ends_at):
            ends_at = make_aware(ends_at)

        if starts_at > now:
            delta = starts_at - now
            days = delta.days
            hours = delta.seconds // 3600

            if days > 0:
                return f"Dans {days} jour{'s' if days > 1 else ''}"
            elif hours > 0:
                return f"Dans {hours} heure{'s' if hours > 1 else ''}"
            else:
                return "Commence bientôt"
        elif ends_at and ends_at > now:
            return "En cours"
        else:
            return "Terminé"


# ==================== PROJECT SERIALIZERS ====================

class ProjectSerializer(serializers.ModelSerializer):
    """Serializer pour les projets"""
    post_title = serializers.CharField(source='post.title', read_only=True)
    status_display = serializers.SerializerMethodField()
    team_members = UserBasicSerializer(source='team', many=True, read_only=True)
    team_count = serializers.SerializerMethodField()
    is_team_member = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'post', 'post_title', 'status', 'status_display',
            'repo_url', 'demo_url', 'team_members', 'team_count',
            'looking_for_members', 'required_skills', 'is_team_member'
        ]
    
    def get_status_display(self, obj):
        """Statut avec emoji"""
        statuses = {
            'draft': {'emoji': '📝', 'label': 'Brouillon', 'color': 'gray'},
            'active': {'emoji': '🚀', 'label': 'Actif', 'color': 'green'},
            'completed': {'emoji': '✅', 'label': 'Terminé', 'color': 'blue'},
            'archived': {'emoji': '📦', 'label': 'Archivé', 'color': 'orange'},
        }
        return statuses.get(obj.status, statuses['active'])
    
    def get_team_count(self, obj):
        return obj.team.count()
    
    def get_is_team_member(self, obj):
        """Vérifie si l'utilisateur est membre"""
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        
        return obj.team.filter(id=request.user.id).exists()


# ==================== INTERACTION SERIALIZERS ====================

class ReactionSerializer(serializers.ModelSerializer):
    """Serializer pour les réactions"""
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = Reaction
        fields = ['id', 'user', 'post', 'kind', 'created_at']
        read_only_fields = ['user', 'created_at']


class ReplySerializer(serializers.ModelSerializer):
    """Serializer pour les réponses (pas de récursion)."""
    user = UserBasicSerializer(read_only=True)
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'post', 'parent', 'content',
            'created_at', 'updated_at', 'is_edited', 'can_edit',
        ]
        read_only_fields = ['user', 'created_at', 'is_edited']

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if not request or not request.user:
            return False
        return obj.user == request.user


class CommentSerializer(serializers.ModelSerializer):
    """Serializer pour les commentaires avec réponses imbriquées."""
    user = UserBasicSerializer(read_only=True)
    replies_count = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    replies = ReplySerializer(many=True, read_only=True)
    likes_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'id', 'user', 'post', 'parent', 'content',
            'created_at', 'updated_at', 'is_edited',
            'replies_count', 'can_edit', 'replies',
            'likes_count', 'is_liked',
        ]
        read_only_fields = ['user', 'created_at', 'is_edited']

    def get_replies_count(self, obj):
        return obj.replies.count()

    def get_can_edit(self, obj):
        request = self.context.get('request')
        if not request or not request.user:
            return False
        return obj.user == request.user

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return obj.likes.filter(user=request.user).exists()


class CommentCreateSerializer(serializers.ModelSerializer):
    """Serializer léger pour créer / modifier un commentaire."""

    class Meta:
        model = Comment
        fields = ['post', 'parent', 'content']

    def validate_content(self, value):
        v = value.strip()
        if not v:
            raise serializers.ValidationError("Le contenu ne peut pas être vide.")
        return v


class ApplicationSerializer(serializers.ModelSerializer):
    """Serializer pour les candidatures"""
    candidate = UserBasicSerializer(source='user', read_only=True)
    opportunity_title = serializers.CharField(source='opportunity.post.title', read_only=True)
    status_display = serializers.SerializerMethodField()
    resume_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Application
        fields = [
            'id', 'candidate', 'opportunity', 'opportunity_title',
            'resume', 'resume_url', 'cover_letter', 'portfolio_url',
            'status', 'status_display', 'created_at', 'updated_at'
        ]
        read_only_fields = ['candidate', 'created_at', 'updated_at']
    
    def get_status_display(self, obj):
        """Statut avec emoji"""
        statuses = {
            'submitted': {'emoji': '📤', 'label': 'Soumise', 'color': '#17a2b8'},
            'viewed': {'emoji': '👁️', 'label': 'Vue', 'color': '#ffc107'},
            'shortlisted': {'emoji': '⭐', 'label': 'Présélectionné', 'color': '#28a745'},
            'interview': {'emoji': '💬', 'label': 'Entretien', 'color': '#007bff'},
            'rejected': {'emoji': '❌', 'label': 'Rejetée', 'color': '#dc3545'},
            'accepted': {'emoji': '✅', 'label': 'Acceptée', 'color': '#28a745'},
        }
        return statuses.get(obj.status, statuses['submitted'])
    
    def get_resume_url(self, obj):
        if not obj.resume:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.resume.url) if request else obj.resume.url


class RSVPSerializer(serializers.ModelSerializer):
    """Serializer pour les RSVP"""
    user = UserBasicSerializer(read_only=True)
    event_title = serializers.CharField(source='event.post.title', read_only=True)
    
    class Meta:
        model = RSVP
        fields = [
            'id', 'user', 'event', 'event_title',
            'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'created_at']


class BookmarkSerializer(serializers.ModelSerializer):
    """Serializer pour les sauvegardes"""
    post_preview = PostListSerializer(source='post', read_only=True)
    
    class Meta:
        model = Bookmark
        fields = ['id', 'post', 'post_preview', 'created_at']
        read_only_fields = ['created_at']