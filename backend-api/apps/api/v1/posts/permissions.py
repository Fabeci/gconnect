"""
G-Connect - Permissions
Classes de permissions personnalisées pour toutes les applications
"""

from rest_framework import permissions


# ==================== PERMISSIONS GÉNÉRALES ====================

class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Permission : l'auteur peut modifier, les autres peuvent seulement lire
    """
    def has_object_permission(self, request, view, obj):
        # Lecture autorisée pour tout le monde
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Écriture seulement pour l'auteur
        return obj.author == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Permission : le propriétaire peut modifier, les autres peuvent seulement lire
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return obj.user == request.user


# ==================== PERMISSIONS ESTABLISHMENTS ====================

class IsInstitutionAdmin(permissions.BasePermission):
    """
    Permission : seulement les admins d'établissement
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'institution_admin_profile')
        )
    
    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'institution_admin_profile'):
            return False
        
        # Vérifier que l'admin appartient à l'établissement
        if hasattr(obj, 'institution'):
            return obj.institution == request.user.institution_admin_profile.institution
        
        return False


class IsInstitutionAdminOrReadOnly(permissions.BasePermission):
    """
    Permission : admin peut modifier, autres peuvent lire
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'institution_admin_profile')
        )
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not hasattr(request.user, 'institution_admin_profile'):
            return False
        
        if hasattr(obj, 'institution'):
            return obj.institution == request.user.institution_admin_profile.institution
        
        return False


class IsPromotionDelegate(permissions.BasePermission):
    """
    Permission : seulement les délégués de promotion
    """
    def has_object_permission(self, request, view, obj):
        if not hasattr(request.user, 'student_profile'):
            return False
        
        # Vérifier si l'utilisateur est délégué de la promotion
        if hasattr(obj, 'promotion'):
            return obj.promotion.members.filter(
                student=request.user.student_profile,
                is_delegate=True,
                is_approved=True
            ).exists()
        
        return False


class IsPromotionDelegateOrInstitutionAdmin(permissions.BasePermission):
    """
    Permission : délégué de promotion ou admin établissement
    """
    def has_object_permission(self, request, view, obj):
        # Admin d'établissement
        if hasattr(request.user, 'institution_admin_profile'):
            if hasattr(obj, 'promotion'):
                return obj.promotion.institution == request.user.institution_admin_profile.institution
        
        # Délégué de promotion
        if hasattr(request.user, 'student_profile'):
            if hasattr(obj, 'promotion'):
                return obj.promotion.members.filter(
                    student=request.user.student_profile,
                    is_delegate=True,
                    is_approved=True
                ).exists()
        
        return False


class IsPromotionMember(permissions.BasePermission):
    """
    Permission : membre approuvé de la promotion
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Vérifier si c'est un étudiant membre
        if hasattr(request.user, 'student_profile'):
            if hasattr(obj, 'promotion'):
                return obj.promotion.members.filter(
                    student=request.user.student_profile,
                    is_approved=True
                ).exists()
        
        # Vérifier si c'est un alumni membre
        if hasattr(request.user, 'alumni_profile'):
            if hasattr(obj, 'promotion'):
                return obj.promotion.alumni_members.filter(
                    alumni=request.user.alumni_profile,
                    is_approved=True
                ).exists()
        
        return False


# ==================== PERMISSIONS MESSAGING ====================

class IsConversationParticipant(permissions.BasePermission):
    """
    Permission : participant actif de la conversation
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Pour un message, vérifier la conversation parent
        if hasattr(obj, 'conversation'):
            conversation = obj.conversation
        else:
            conversation = obj
        
        # Vérifier que l'utilisateur est participant actif
        return conversation.memberships.filter(
            user=request.user,
            is_active=True
        ).exists()


class IsConversationAdmin(permissions.BasePermission):
    """
    Permission : admin de la conversation (groupes seulement)
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Pour un message ou participant, récupérer la conversation
        if hasattr(obj, 'conversation'):
            conversation = obj.conversation
        else:
            conversation = obj
        
        # Vérifier le rôle admin
        return conversation.memberships.filter(
            user=request.user,
            is_active=True,
            role='admin'
        ).exists()


class IsMessageSender(permissions.BasePermission):
    """
    Permission : expéditeur du message
    """
    def has_object_permission(self, request, view, obj):
        return obj.sender == request.user


class IsMessageSenderOrReadOnly(permissions.BasePermission):
    """
    Permission : expéditeur peut modifier, autres peuvent lire
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return obj.sender == request.user


# ==================== PERMISSIONS POSTS ====================

class CanViewPost(permissions.BasePermission):
    """
    Permission : peut voir le post selon l'audience
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            # Non connecté : seulement posts publics
            return obj.audience == 'public'
        
        # Utiliser la méthode can_user_view du modèle
        return obj.can_user_view(request.user)


class IsPostAuthor(permissions.BasePermission):
    """
    Permission : auteur du post
    """
    def has_object_permission(self, request, view, obj):
        return obj.author == request.user


class IsPostAuthorOrReadOnly(permissions.BasePermission):
    """
    Permission : auteur peut modifier, autres peuvent lire
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            # Vérifier d'abord la visibilité
            if hasattr(obj, 'can_user_view'):
                return obj.can_user_view(request.user)
            return True
        
        return obj.author == request.user


class IsOpportunityAuthor(permissions.BasePermission):
    """
    Permission : auteur de l'opportunité (via post)
    """
    def has_object_permission(self, request, view, obj):
        return obj.post.author == request.user


class IsOpportunityAuthorOrReadOnly(permissions.BasePermission):
    """
    Permission : auteur peut modifier, autres peuvent lire
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return obj.post.author == request.user


class CanApplyToOpportunity(permissions.BasePermission):
    """
    Permission : peut postuler à l'opportunité
    """
    def has_permission(self, request, view):
        # Doit être connecté
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Ne peut pas postuler si c'est son propre post
        opportunity_id = view.kwargs.get('pk')
        if opportunity_id:
            from apps.api.v1.posts.models import Opportunity
            opportunity = Opportunity.objects.filter(id=opportunity_id).first()
            if opportunity and opportunity.post.author == request.user:
                return False
        
        return True


class IsEventAuthor(permissions.BasePermission):
    """
    Permission : auteur de l'événement
    """
    def has_object_permission(self, request, view, obj):
        return obj.post.author == request.user


class IsProjectAuthorOrTeamMember(permissions.BasePermission):
    """
    Permission : auteur du projet ou membre de l'équipe
    """
    def has_object_permission(self, request, view, obj):
        # Auteur du post
        if obj.post.author == request.user:
            return True
        
        # Membre de l'équipe
        return obj.team.filter(id=request.user.id).exists()


class IsCommentAuthor(permissions.BasePermission):
    """
    Permission : auteur du commentaire
    """
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


# ==================== PERMISSIONS COMPOSÉES ====================

class IsAdminOrAuthor(permissions.BasePermission):
    """
    Permission : superadmin ou auteur
    """
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        
        if hasattr(obj, 'author'):
            return obj.author == request.user
        
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission : admin pour écriture, lecture pour tous
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return request.user and request.user.is_staff