"""
G-Connect - Messaging Views
ViewSets pour l'application de messagerie
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch, Q, Max, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404

from apps.api.v1.messaging.models import (
    Conversation, ConversationParticipant, Message,
    MessageReaction, MessageReadReceipt, TypingIndicator
)
from .pagination import ConversationPagination, MessagePagination
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer,
    ConversationCreateSerializer, MessageSerializer,
    MessageCreateSerializer, MessageReactionSerializer,
    TypingIndicatorSerializer, AddParticipantsSerializer,
    RemoveParticipantSerializer
)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les conversations
    
    list: Liste toutes les conversations de l'utilisateur
    retrieve: Détails d'une conversation
    create: Créer une nouvelle conversation (directe ou groupe)
    update/partial_update: Modifier une conversation (groupes seulement)
    destroy: Supprimer/archiver une conversation
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = ConversationPagination

    def get_queryset(self):
        """Retourne seulement les conversations de l'utilisateur.
        `memberships` est préchargé (select_related('user')) une fois pour
        toute la page — le serializer le réutilise (`.all()`) au lieu de
        refaire un `.filter()` par ligne pour other_participant/unread_count/
        participants_count/is_muted (jusqu'à 5 requêtes redondantes par
        conversation avant ce correctif)."""
        return Conversation.objects.filter(
            memberships__user=self.request.user,
            memberships__is_active=True
        ).annotate(
            last_message_time=Max('messages__created_at')
        ).prefetch_related(
            Prefetch('memberships', queryset=ConversationParticipant.objects.select_related('user'))
        ).order_by('-last_message_time').distinct()
    
    def get_serializer_class(self):
        """Utilise différents serializers selon l'action"""
        if self.action == 'list':
            return ConversationListSerializer
        elif self.action == 'create':
            return ConversationCreateSerializer
        return ConversationDetailSerializer

    def create(self, request, *args, **kwargs):
        """"Récupérer ou créer" : valide via ConversationCreateSerializer
        (write-only, participant_ids). Pour une conversation directe déjà
        existante avec cet utilisateur, renvoie celle-ci (200) au lieu de
        lever une erreur ou d'en créer une seconde. Renvoie toujours le
        détail complet (id, participants...) via ConversationDetailSerializer
        — sinon le client n'a aucun moyen de récupérer l'id pour ouvrir
        l'écran de chat."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        was_existing = serializer._existing_conversation is not None
        conversation = serializer.save()
        detail = ConversationDetailSerializer(conversation, context=self.get_serializer_context())
        if was_existing:
            return Response(detail.data, status=status.HTTP_200_OK)
        headers = self.get_success_headers(detail.data)
        return Response(detail.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_destroy(self, instance):
        """Archive plutôt que supprimer"""
        # Marquer comme inactif pour l'utilisateur
        membership = instance.memberships.filter(user=self.request.user).first()
        if membership:
            membership.is_active = False
            membership.left_at = timezone.now()
            membership.save()
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archiver une conversation"""
        conversation = self.get_object()
        conversation.is_archived = True
        conversation.save()
        return Response({'status': 'conversation archivée'})
    
    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Désarchiver une conversation"""
        conversation = self.get_object()
        conversation.is_archived = False
        conversation.save()
        return Response({'status': 'conversation désarchivée'})
    
    @action(detail=True, methods=['post'])
    def mute(self, request, pk=None):
        """Mettre en sourdine"""
        conversation = self.get_object()
        duration = request.data.get('duration', None)  # en secondes
        
        membership = conversation.memberships.filter(user=request.user).first()
        if not membership:
            return Response(
                {'error': 'Vous ne faites pas partie de cette conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        membership.is_muted = True
        membership.notifications_enabled = False
        
        if duration:
            membership.muted_until = timezone.now() + timezone.timedelta(seconds=duration)
        else:
            membership.muted_until = None  # Sourdine permanente
        
        membership.save()
        
        return Response({
            'status': 'conversation en sourdine',
            'muted_until': membership.muted_until
        })
    
    @action(detail=True, methods=['post'])
    def unmute(self, request, pk=None):
        """Retirer la sourdine"""
        conversation = self.get_object()
        
        membership = conversation.memberships.filter(user=request.user).first()
        if not membership:
            return Response(
                {'error': 'Vous ne faites pas partie de cette conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        membership.is_muted = False
        membership.muted_until = None
        membership.notifications_enabled = True
        membership.save()
        
        return Response({'status': 'sourdine retirée'})
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marquer tous les messages comme lus"""
        conversation = self.get_object()
        
        membership = conversation.memberships.filter(user=request.user).first()
        if not membership:
            return Response(
                {'error': 'Vous ne faites pas partie de cette conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Capturer l'ancien seuil AVANT mark_as_read() : celle-ci écrase
        # immédiatement last_read_at avec l'heure actuelle, donc l'utiliser
        # après pour filtrer les messages "non lus" ne matchait plus jamais
        # rien (created_at__gt=maintenant) — aucun accusé de lecture n'était
        # jamais créé après le tout premier appel.
        previous_last_read_at = membership.last_read_at
        membership.mark_as_read()

        # Créer des read receipts pour tous les messages non lus
        unread_messages = conversation.messages.filter(
            created_at__gt=previous_last_read_at
        ).exclude(sender=request.user) if previous_last_read_at else (
            conversation.messages.exclude(sender=request.user)
        )

        for message in unread_messages:
            MessageReadReceipt.objects.get_or_create(
                message=message,
                user=request.user
            )
        
        return Response({
            'status': 'messages marqués comme lus',
            'unread_count': 0
        })
    
    @action(detail=True, methods=['post'])
    def add_participants(self, request, pk=None):
        """Ajouter des participants (groupes seulement)"""
        conversation = self.get_object()
        
        # Vérifier que c'est un groupe
        if conversation.conversation_type != Conversation.ConversationType.GROUP:
            return Response(
                {'error': 'Impossible d\'ajouter des participants à une conversation directe'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier que l'utilisateur est admin
        membership = conversation.memberships.filter(
            user=request.user,
            role=ConversationParticipant.Role.ADMIN
        ).first()
        
        if not membership:
            return Response(
                {'error': 'Seuls les admins peuvent ajouter des participants'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = AddParticipantsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_ids = serializer.validated_data['user_ids']
        added_count = 0
        
        for user_id in user_ids:
            # Vérifier que l'utilisateur n'est pas déjà participant
            if not conversation.memberships.filter(user_id=user_id).exists():
                ConversationParticipant.objects.create(
                    conversation=conversation,
                    user_id=user_id
                )
                added_count += 1
        
        return Response({
            'status': f'{added_count} participant(s) ajouté(s)',
            'participants_count': conversation.memberships.filter(is_active=True).count()
        })
    
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        """Retirer un participant (groupes seulement)"""
        conversation = self.get_object()
        
        # Vérifier que c'est un groupe
        if conversation.conversation_type != Conversation.ConversationType.GROUP:
            return Response(
                {'error': 'Impossible de retirer des participants d\'une conversation directe'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier que l'utilisateur est admin
        membership = conversation.memberships.filter(
            user=request.user,
            role=ConversationParticipant.Role.ADMIN
        ).first()
        
        if not membership:
            return Response(
                {'error': 'Seuls les admins peuvent retirer des participants'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = RemoveParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        
        # Ne pas permettre de se retirer soi-même via cette route
        if user_id == request.user.id:
            return Response(
                {'error': 'Utilisez l\'action "leave" pour quitter le groupe'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        participant = conversation.memberships.filter(user_id=user_id).first()
        if not participant:
            return Response(
                {'error': 'Participant non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        participant.is_active = False
        participant.left_at = timezone.now()
        participant.save()
        
        return Response({
            'status': 'participant retiré',
            'participants_count': conversation.memberships.filter(is_active=True).count()
        })
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Quitter une conversation"""
        conversation = self.get_object()

        membership = conversation.memberships.filter(user=request.user).first()
        if not membership:
            return Response(
                {'error': 'Vous ne faites pas partie de cette conversation'},
                status=status.HTTP_404_NOT_FOUND
            )

        membership.is_active = False
        membership.left_at = timezone.now()
        membership.save()

        return Response({'status': 'conversation quittée'})

    @action(detail=True, methods=['post'])
    def clear(self, request, pk=None):
        """Vider tous les messages de la conversation (soft-delete côté utilisateur)."""
        conversation = self.get_object()

        if not conversation.memberships.filter(user=request.user, is_active=True).exists():
            return Response(
                {'error': 'Vous ne faites pas partie de cette conversation'},
                status=status.HTTP_403_FORBIDDEN,
            )

        now = timezone.now()
        updated = conversation.messages.filter(is_deleted=False).update(
            is_deleted=True,
            deleted_at=now,
            content='',
        )
        return Response({'status': 'conversation vidée', 'deleted_count': updated})


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les messages
    
    list: Liste les messages d'une conversation
    create: Envoyer un nouveau message
    retrieve: Détails d'un message
    update/partial_update: Modifier un message
    destroy: Supprimer un message
    """
    
    permission_classes = [IsAuthenticated]
    pagination_class = MessagePagination

    def get_queryset(self):
        """Retourne les messages des conversations de l'utilisateur."""
        conversation_id = self.request.query_params.get('conversation', None)

        queryset = Message.objects.filter(
            conversation__memberships__user=self.request.user,
            conversation__memberships__is_active=True,
            is_deleted=False,
        ).select_related('sender', 'reply_to').prefetch_related(
            'attachments', 'reactions', 'read_receipts'
        ).distinct().order_by('-created_at')

        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
            # Mettre à jour last_seen du participant courant pour cette conversation.
            ConversationParticipant.objects.filter(
                conversation_id=conversation_id,
                user=self.request.user,
            ).update(last_seen=timezone.now(), is_online=True)

        return queryset
    
    def get_serializer_class(self):
        """Utilise différents serializers selon l'action"""
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer

    def create(self, request, *args, **kwargs):
        """Valide/crée via MessageCreateSerializer (payload minimal) mais
        renvoie le message complet (id, sender, created_at...) via
        MessageSerializer — sinon le client ne peut ni afficher la bulle
        envoyée ni faire défiler jusqu'à elle."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        detail = MessageSerializer(message, context=self.get_serializer_context())
        headers = self.get_success_headers(detail.data)
        return Response(detail.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_update(self, serializer):
        """Marque le message comme édité"""
        serializer.save(
            is_edited=True,
            edited_at=timezone.now()
        )
    
    def perform_destroy(self, instance):
        """Soft delete du message"""
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.content = ""  # Effacer le contenu
        instance.save()
    
    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """Réagir à un message"""
        message = self.get_object()
        reaction_type = request.data.get('reaction_type', 'like')
        
        # Créer ou mettre à jour la réaction
        reaction, created = MessageReaction.objects.update_or_create(
            message=message,
            user=request.user,
            defaults={'reaction_type': reaction_type}
        )
        
        serializer = MessageReactionSerializer(reaction, context={'request': request})
        
        return Response({
            'status': 'réaction ajoutée' if created else 'réaction mise à jour',
            'reaction': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def unreact(self, request, pk=None):
        """Retirer une réaction"""
        message = self.get_object()
        
        deleted_count = MessageReaction.objects.filter(
            message=message,
            user=request.user
        ).delete()[0]
        
        if deleted_count > 0:
            return Response({'status': 'réaction retirée'})
        
        return Response(
            {'error': 'Aucune réaction trouvée'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Marquer un message comme lu"""
        message = self.get_object()
        
        # Ne pas créer de read receipt pour ses propres messages
        if message.sender == request.user:
            return Response({'status': 'propre message, non marqué'})
        
        receipt, created = MessageReadReceipt.objects.get_or_create(
            message=message,
            user=request.user
        )
        
        # Mettre à jour le compteur non lu
        membership = message.conversation.memberships.filter(user=request.user).first()
        if membership and membership.unread_count > 0:
            membership.unread_count -= 1
            membership.last_read_at = timezone.now()
            membership.save()
        
        return Response({
            'status': 'message marqué comme lu' if created else 'déjà lu'
        })


class TypingIndicatorViewSet(viewsets.ViewSet):
    """
    ViewSet pour les indicateurs de saisie
    """
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def start(self, request):
        """Indiquer qu'on est en train d'écrire"""
        conversation_id = request.data.get('conversation_id')
        
        if not conversation_id:
            return Response(
                {'error': 'conversation_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Vérifier que l'utilisateur fait partie de la conversation
        if not conversation.memberships.filter(user=request.user, is_active=True).exists():
            return Response(
                {'error': 'Vous ne faites pas partie de cette conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Créer ou mettre à jour l'indicateur
        indicator, created = TypingIndicator.objects.update_or_create(
            conversation=conversation,
            user=request.user
        )
        
        return Response({'status': 'typing indicator started'})
    
    @action(detail=False, methods=['post'])
    def stop(self, request):
        """Arrêter l'indicateur de saisie"""
        conversation_id = request.data.get('conversation_id')
        
        if not conversation_id:
            return Response(
                {'error': 'conversation_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        TypingIndicator.objects.filter(
            conversation_id=conversation_id,
            user=request.user
        ).delete()
        
        return Response({'status': 'typing indicator stopped'})
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Liste les utilisateurs en train d'écrire dans une conversation"""
        conversation_id = request.query_params.get('conversation_id')
        
        if not conversation_id:
            return Response(
                {'error': 'conversation_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Nettoyer les anciens indicateurs (> 10 secondes)
        cutoff = timezone.now() - timezone.timedelta(seconds=10)
        TypingIndicator.objects.filter(started_at__lt=cutoff).delete()
        
        # Récupérer les indicateurs actifs (sauf l'utilisateur courant)
        indicators = TypingIndicator.objects.filter(
            conversation_id=conversation_id
        ).exclude(user=request.user).select_related('user')
        
        serializer = TypingIndicatorSerializer(
            indicators,
            many=True,
            context={'request': request}
        )
        
        return Response(serializer.data)