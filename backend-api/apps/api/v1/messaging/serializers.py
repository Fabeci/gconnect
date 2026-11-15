"""
G-Connect - Messaging Serializers (COMPLETS)
Serializers pour l'application de messagerie avec toutes les fonctionnalités
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from apps.api.v1.messaging.models import (
    Conversation, ConversationParticipant, Message, MessageAttachment,
    MessageReaction, MessageReadReceipt, TypingIndicator
)

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les informations utilisateur"""
    full_name = serializers.SerializerMethodField()
    photo_url = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        ref_name = "MessagingUserBasic"
        fields = ['id', 'username', 'full_name', 'photo_url', 'role', 'is_online']
    
    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username
    
    def get_photo_url(self, obj):
        request = self.context.get('request')
        if obj.photo:
            return request.build_absolute_uri(obj.photo.url) if request else obj.photo.url
        return None
    
    def get_is_online(self, obj):
        """Vérifie si l'utilisateur est en ligne (basé sur last_seen < 5min)"""
        # Logique à implémenter selon votre système
        return False


class MessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer pour les pièces jointes"""
    url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    size_display = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageAttachment
        fields = [
            'id', 'file_name', 'file_size', 'size_display', 'mime_type',
            'url', 'thumbnail_url', 'width', 'height', 'duration'
        ]
    
    def get_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url
    
    def get_thumbnail_url(self, obj):
        if not obj.thumbnail:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(obj.thumbnail.url) if request else obj.thumbnail.url
    
    def get_size_display(self, obj):
        """Formatte la taille du fichier"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class MessageReactionSerializer(serializers.ModelSerializer):
    """Serializer pour les réactions aux messages"""
    user = UserBasicSerializer(read_only=True)
    emoji = serializers.SerializerMethodField()
    
    class Meta:
        model = MessageReaction
        fields = ['id', 'user', 'reaction_type', 'emoji', 'created_at']
    
    def get_emoji(self, obj):
        """Retourne l'emoji correspondant au type"""
        emojis = {
            'like': '👍',
            'love': '❤️',
            'laugh': '😂',
            'wow': '😮',
            'sad': '😢',
            'angry': '😡',
            'fire': '🔥',
            'clap': '👏',
            'celebrate': '🎉',
        }
        return emojis.get(obj.reaction_type, '👍')


class MessageReadReceiptSerializer(serializers.ModelSerializer):
    """Serializer pour les accusés de lecture"""
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = MessageReadReceipt
        fields = ['id', 'user', 'read_at']


class MessageSerializer(serializers.ModelSerializer):
    """Serializer pour les messages"""
    sender = UserBasicSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    reactions = MessageReactionSerializer(many=True, read_only=True)
    reply_to_message = serializers.SerializerMethodField()
    reactions_summary = serializers.SerializerMethodField()
    read_receipts = MessageReadReceiptSerializer(many=True, read_only=True)
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'message_type', 'content',
            'reply_to', 'reply_to_message', 'attachments', 'reactions',
            'reactions_summary', 'read_receipts', 'is_read',
            'created_at', 'edited_at', 'is_edited', 'is_deleted', 'delivered_at'
        ]
        read_only_fields = ['id', 'sender', 'created_at', 'is_edited']
    
    def get_reply_to_message(self, obj):
        """Retourne un aperçu du message auquel on répond"""
        if not obj.reply_to:
            return None
        return {
            'id': obj.reply_to.id,
            'sender': UserBasicSerializer(obj.reply_to.sender, context=self.context).data,
            'content': obj.reply_to.content[:100],
            'message_type': obj.reply_to.message_type
        }
    
    def get_reactions_summary(self, obj):
        """Résumé groupé des réactions"""
        reactions = {}
        emojis = {
            'like': '👍', 'love': '❤️', 'laugh': '😂', 'wow': '😮',
            'sad': '😢', 'angry': '😡', 'fire': '🔥', 'clap': '👏', 'celebrate': '🎉'
        }
        
        for reaction in obj.reactions.all():
            reaction_type = reaction.reaction_type
            emoji = emojis.get(reaction_type, '👍')
            
            if reaction_type not in reactions:
                reactions[reaction_type] = {
                    'emoji': emoji,
                    'count': 0,
                    'users': []
                }
            
            reactions[reaction_type]['count'] += 1
            reactions[reaction_type]['users'].append({
                'id': reaction.user.id,
                'username': reaction.user.username
            })
        
        return reactions
    
    def get_is_read(self, obj):
        """Vérifie si le message a été lu par l'utilisateur courant"""
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            return False
        
        if obj.sender == request.user:
            return True  # Propre message
        
        return obj.read_receipts.filter(user=request.user).exists()
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user:
            validated_data['sender'] = request.user
        return super().create(validated_data)


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour la création de messages"""
    attachment_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Message
        fields = ['conversation', 'message_type', 'content', 'reply_to', 'attachment_files']
    
    def validate(self, data):
        """Validation du message"""
        # Au moins un contenu (texte ou fichier)
        if not data.get('content') and not data.get('attachment_files'):
            raise serializers.ValidationError(
                "Le message doit contenir du texte ou au moins un fichier."
            )
        
        # Vérifier que l'utilisateur fait partie de la conversation
        request = self.context.get('request')
        conversation = data.get('conversation')
        
        if not conversation.memberships.filter(user=request.user, is_active=True).exists():
            raise serializers.ValidationError(
                "Vous ne faites pas partie de cette conversation."
            )
        
        return data
    
    def create(self, validated_data):
        attachment_files = validated_data.pop('attachment_files', [])
        request = self.context.get('request')
        
        # Créer le message
        message = Message.objects.create(
            sender=request.user,
            **validated_data
        )
        
        # Créer les attachments
        for idx, file in enumerate(attachment_files):
            # Déterminer le type
            mime_type = getattr(file, 'content_type', '')
            if mime_type.startswith('image/'):
                kind = MessageAttachment.Kind.IMAGE
            elif mime_type.startswith('video/'):
                kind = MessageAttachment.Kind.VIDEO
            else:
                kind = MessageAttachment.Kind.FILE
            
            MessageAttachment.objects.create(
                message=message,
                file=file,
                file_name=file.name,
                file_size=file.size,
                mime_type=mime_type,
                kind=kind,
                order=idx
            )
        
        return message


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """Serializer pour les participants d'une conversation"""
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = ConversationParticipant
        fields = [
            'id', 'user', 'role', 'is_online', 'last_seen',
            'unread_count', 'notifications_enabled', 'is_muted',
            'muted_until', 'joined_at', 'is_active'
        ]
        read_only_fields = ['unread_count', 'joined_at']


class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des conversations (vue compacte)"""
    other_participant = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    display_photo = serializers.SerializerMethodField()
    participants_count = serializers.SerializerMethodField()
    is_muted = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'name', 'display_name',
            'display_photo', 'other_participant', 'last_message',
            'last_message_at', 'unread_count', 'participants_count',
            'is_archived', 'is_muted', 'created_at'
        ]
    
    def _memberships(self, obj):
        """Liste des memberships — utilise le cache prefetch_related de la
        vue (`obj.memberships.all()`), jamais `.filter()` qui le contournerait."""
        return obj.memberships.all()

    def _other_membership(self, obj, current_user):
        """Mémoïsé sur l'instance : 3 champs (other_participant, display_name,
        display_photo) appelaient chacun une requête `.exclude().first()`
        séparée sur le M2M `participants` — remplacé par une seule recherche
        dans les memberships déjà prefetchés."""
        if not hasattr(obj, '_other_membership_cache'):
            obj._other_membership_cache = next(
                (m for m in self._memberships(obj) if m.user_id != current_user.id), None
            )
        return obj._other_membership_cache

    def _my_membership(self, obj, current_user):
        """Mémoïsé sur l'instance : unread_count et is_muted appelaient
        chacun `.filter(user=...).first()` séparément."""
        if not hasattr(obj, '_my_membership_cache'):
            obj._my_membership_cache = next(
                (m for m in self._memberships(obj) if m.user_id == current_user.id), None
            )
        return obj._my_membership_cache

    def get_other_participant(self, obj):
        """Pour les conversations directes, retourne l'autre participant avec statut en ligne réel."""
        request = self.context.get('request')
        if obj.conversation_type == Conversation.ConversationType.DIRECT and request:
            membership = self._other_membership(obj, request.user)
            other = membership.user if membership else None
            if not other:
                return None
            data = UserBasicSerializer(other, context=self.context).data
            if membership:
                cutoff = timezone.now() - timedelta(minutes=5)
                data['is_online'] = (
                    membership.last_seen is not None and membership.last_seen >= cutoff
                )
                data['last_seen'] = (
                    membership.last_seen.isoformat() if membership.last_seen else None
                )
            return data
        return None
    
    def get_last_message(self, obj):
        """Retourne le dernier message"""
        last_msg = obj.messages.filter(is_deleted=False).order_by('-created_at').first()
        if not last_msg:
            return None
        
        content = last_msg.content
        if last_msg.is_deleted:
            content = "Message supprimé"
        elif last_msg.message_type == Message.MessageType.IMAGE:
            content = "📷 Image"
        elif last_msg.message_type == Message.MessageType.VIDEO:
            content = "🎥 Vidéo"
        elif last_msg.message_type == Message.MessageType.AUDIO:
            content = "🎵 Audio"
        elif last_msg.message_type == Message.MessageType.FILE:
            content = "📎 Fichier"
        elif last_msg.message_type == Message.MessageType.VOICE:
            content = "🎤 Message vocal"
        
        return {
            'id': last_msg.id,
            'sender_id': last_msg.sender.id if last_msg.sender else None,
            'sender_name': last_msg.sender.get_full_name() if last_msg.sender else "Utilisateur supprimé",
            'content': content[:100],
            'message_type': last_msg.message_type,
            'created_at': last_msg.created_at,
            'is_read': last_msg.read_receipts.filter(user=self.context['request'].user).exists() if self.context.get('request') else False
        }
    
    def get_unread_count(self, obj):
        """Compte les messages non lus pour l'utilisateur courant"""
        request = self.context.get('request')
        if not request or not request.user:
            return 0

        participant = self._my_membership(obj, request.user)
        return participant.unread_count if participant else 0
    
    def get_display_name(self, obj):
        """Nom à afficher pour la conversation"""
        if obj.conversation_type == Conversation.ConversationType.GROUP:
            return obj.name
        
        # Pour les conversations directes
        request = self.context.get('request')
        if request:
            membership = self._other_membership(obj, request.user)
            other = membership.user if membership else None
            return other.get_full_name() if other else "Utilisateur"
        return "Conversation"

    def get_display_photo(self, obj):
        """Photo à afficher pour la conversation"""
        request = self.context.get('request')

        if obj.conversation_type == Conversation.ConversationType.GROUP:
            if obj.group_photo:
                return request.build_absolute_uri(obj.group_photo.url) if request else obj.group_photo.url
            return None

        # Pour les conversations directes
        if request:
            membership = self._other_membership(obj, request.user)
            other = membership.user if membership else None
            if other and other.photo:
                return request.build_absolute_uri(other.photo.url) if request else other.photo.url
        return None
    
    def get_participants_count(self, obj):
        """Nombre de participants"""
        return sum(1 for m in self._memberships(obj) if m.is_active)

    def get_is_muted(self, obj):
        """Vérifie si la conversation est en sourdine pour l'utilisateur"""
        request = self.context.get('request')
        if not request or not request.user:
            return False

        participant = self._my_membership(obj, request.user)
        if not participant:
            return False
        
        if participant.is_muted:
            # Vérifier si la sourdine est encore active
            if participant.muted_until and participant.muted_until < timezone.now():
                participant.is_muted = False
                participant.muted_until = None
                participant.save()
                return False
            return True
        
        return False


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour une conversation"""
    participants = ConversationParticipantSerializer(source='memberships', many=True, read_only=True)
    created_by_user = UserBasicSerializer(source='created_by', read_only=True)
    messages_count = serializers.SerializerMethodField()
    my_membership = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'name', 'description',
            'group_photo', 'created_by_user', 'participants',
            'created_at', 'updated_at', 'last_message_at',
            'is_archived', 'messages_count', 'my_membership'
        ]
    
    def get_messages_count(self, obj):
        return obj.messages.filter(is_deleted=False).count()
    
    def get_my_membership(self, obj):
        """Informations sur l'adhésion de l'utilisateur courant"""
        request = self.context.get('request')
        if not request or not request.user:
            return None
        
        participant = obj.memberships.filter(user=request.user).first()
        if not participant:
            return None
        
        return ConversationParticipantSerializer(participant, context=self.context).data


class ConversationCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer une conversation"""
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=True
    )
    
    class Meta:
        model = Conversation
        fields = ['conversation_type', 'name', 'description', 'group_photo', 'participant_ids']
    
    def validate_participant_ids(self, value):
        """Valide que les IDs correspondent à des utilisateurs existants"""
        if len(value) < 1:
            raise serializers.ValidationError("Au moins un participant est requis.")
        
        # Pour les conversations directes, maximum 2 participants (1 autre + l'auteur)
        if self.initial_data.get('conversation_type') == Conversation.ConversationType.DIRECT:
            if len(value) != 1:
                raise serializers.ValidationError(
                    "Une conversation directe doit avoir exactement 1 autre participant."
                )
        
        # Vérifier que les utilisateurs existent
        existing_users = User.objects.filter(id__in=value).count()
        if existing_users != len(value):
            raise serializers.ValidationError("Certains utilisateurs n'existent pas.")
        
        return value
    
    def validate(self, data):
        """Validation supplémentaire"""
        # Pour les groupes, le nom est requis
        if data.get('conversation_type') == Conversation.ConversationType.GROUP:
            if not data.get('name'):
                raise serializers.ValidationError({
                    'name': "Le nom est requis pour un groupe."
                })
        
        # Conversation directe : "récupérer ou créer" plutôt qu'échouer — si
        # une conversation directe existe déjà avec cet utilisateur, on la
        # mémorise ici pour la renvoyer telle quelle depuis create(), sans
        # jamais créer de doublon.
        self._existing_conversation = None
        if data.get('conversation_type') == Conversation.ConversationType.DIRECT:
            request = self.context.get('request')
            other_user_id = data['participant_ids'][0]

            existing = Conversation.objects.filter(
                conversation_type=Conversation.ConversationType.DIRECT,
                memberships__user=request.user
            ).filter(
                memberships__user_id=other_user_id
            ).distinct().first()

            if existing:
                self._existing_conversation = existing

        return data

    def create(self, validated_data):
        if self._existing_conversation is not None:
            return self._existing_conversation

        participant_ids = validated_data.pop('participant_ids')
        request = self.context.get('request')

        # Créer la conversation
        conversation = Conversation.objects.create(
            created_by=request.user,
            **validated_data
        )
        
        # Ajouter le créateur comme participant (admin pour les groupes)
        role = ConversationParticipant.Role.ADMIN if conversation.conversation_type == Conversation.ConversationType.GROUP else ConversationParticipant.Role.MEMBER
        ConversationParticipant.objects.create(
            conversation=conversation,
            user=request.user,
            role=role
        )
        
        # Ajouter les autres participants
        for user_id in participant_ids:
            if user_id != request.user.id:
                try:
                    user = User.objects.get(id=user_id)
                    ConversationParticipant.objects.create(
                        conversation=conversation,
                        user=user
                    )
                except User.DoesNotExist:
                    pass
        
        return conversation


class TypingIndicatorSerializer(serializers.ModelSerializer):
    """Serializer pour les indicateurs de saisie"""
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = TypingIndicator
        fields = ['conversation', 'user', 'started_at']
        read_only_fields = ['user', 'started_at']


class AddParticipantsSerializer(serializers.Serializer):
    """Serializer pour ajouter des participants à un groupe"""
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        allow_empty=False
    )
    
    def validate_user_ids(self, value):
        """Vérifie que les utilisateurs existent"""
        existing = User.objects.filter(id__in=value).count()
        if existing != len(value):
            raise serializers.ValidationError("Certains utilisateurs n'existent pas.")
        return value


class RemoveParticipantSerializer(serializers.Serializer):
    """Serializer pour retirer un participant"""
    user_id = serializers.IntegerField(required=True)
    
    def validate_user_id(self, value):
        """Vérifie que l'utilisateur existe"""
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Utilisateur inexistant.")
        return value