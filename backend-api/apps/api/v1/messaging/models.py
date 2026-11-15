"""
G-Connect - Messaging Models
Application de messagerie instantanée avec support des conversations individuelles et de groupe
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Conversation(models.Model):
    """
    Modèle pour gérer les conversations (individuelles ou de groupe)
    """
    class ConversationType(models.TextChoices):
        DIRECT = "direct", "Conversation directe"
        GROUP = "group", "Groupe"

    conversation_type = models.CharField(
        max_length=10, 
        choices=ConversationType.choices,
        default=ConversationType.DIRECT
    )
    
    # Pour les conversations de groupe
    name = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True)
    group_photo = models.ImageField(upload_to='conversations/groups/', blank=True, null=True)
    
    # Créateur de la conversation (utile pour les groupes)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_conversations'
    )
    
    # Participants
    participants = models.ManyToManyField(
        User, 
        through='ConversationParticipant',
        related_name='conversations'
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    # Archivage
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['-last_message_at']),
            models.Index(fields=['conversation_type']),
        ]

    def __str__(self):
        if self.conversation_type == self.ConversationType.GROUP:
            return self.name or f"Groupe #{self.id}"
        return f"Conversation #{self.id}"

    def update_last_message_time(self):
        """Met à jour le timestamp du dernier message"""
        self.last_message_at = timezone.now()
        self.save(update_fields=['last_message_at'])

    def get_other_participant(self, current_user):
        """Pour les conversations directes, retourne l'autre participant"""
        if self.conversation_type == self.ConversationType.DIRECT:
            return self.participants.exclude(id=current_user.id).first()
        return None


class ConversationParticipant(models.Model):
    """
    Table intermédiaire pour gérer les participants avec métadonnées
    """
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrateur"
        MEMBER = "member", "Membre"

    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='conversation_memberships'
    )
    
    # Rôle dans le groupe (pour les conversations de groupe)
    role = models.CharField(
        max_length=10, 
        choices=Role.choices,
        default=Role.MEMBER
    )
    
    # Statut en ligne
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    
    # Lecture des messages
    last_read_at = models.DateTimeField(null=True, blank=True)
    unread_count = models.PositiveIntegerField(default=0)
    
    # Notifications
    notifications_enabled = models.BooleanField(default=True)
    is_muted = models.BooleanField(default=False)
    muted_until = models.DateTimeField(null=True, blank=True)
    
    # Métadonnées
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('conversation', 'user')
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['conversation', 'unread_count']),
        ]

    def __str__(self):
        return f"{self.user.username} dans {self.conversation}"

    def mark_as_read(self):
        """Marque tous les messages comme lus"""
        self.last_read_at = timezone.now()
        self.unread_count = 0
        self.save(update_fields=['last_read_at', 'unread_count'])


class Message(models.Model):
    """
    Modèle pour les messages dans une conversation
    """
    class MessageType(models.TextChoices):
        TEXT = "text", "Texte"
        IMAGE = "image", "Image"
        VIDEO = "video", "Vidéo"
        AUDIO = "audio", "Audio"
        FILE = "file", "Fichier"
        VOICE = "voice", "Message vocal"
        SYSTEM = "system", "Message système"

    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_messages'
    )
    
    # Contenu
    message_type = models.CharField(
        max_length=10, 
        choices=MessageType.choices,
        default=MessageType.TEXT
    )
    content = models.TextField(blank=True)
    
    # Réponse à un message
    reply_to = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='replies'
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)
    
    # Suppression
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Statut de livraison
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]

    def __str__(self):
        return f"Message de {self.sender.username if self.sender else 'Système'} - {self.created_at}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Mettre à jour le dernier message de la conversation
        if is_new and not self.is_deleted:
            self.conversation.update_last_message_time()
            
            # Incrémenter le compteur de messages non lus pour tous les participants sauf l'expéditeur
            self.conversation.memberships.exclude(user=self.sender).update(
                unread_count=models.F('unread_count') + 1
            )


class MessageAttachment(models.Model):
    """
    Pièces jointes aux messages
    """
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='messages/attachments/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="Taille en bytes")
    mime_type = models.CharField(max_length=100, blank=True)
    
    # Pour les images
    thumbnail = models.ImageField(upload_to='messages/thumbnails/', blank=True, null=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    
    # Pour les audios/vidéos
    duration = models.PositiveIntegerField(null=True, blank=True, help_text="Durée en secondes")
    
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"Attachment: {self.file_name}"


class MessageReaction(models.Model):
    """
    Réactions aux messages (émojis)
    """
    class ReactionType(models.TextChoices):
        LIKE = "like", "👍 Like"
        LOVE = "love", "❤️ Love"
        LAUGH = "laugh", "😂 Laugh"
        WOW = "wow", "😮 Wow"
        SAD = "sad", "😢 Sad"
        ANGRY = "angry", "😡 Angry"
        FIRE = "fire", "🔥 Fire"
        CLAP = "clap", "👏 Clap"
        CELEBRATE = "celebrate", "🎉 Celebrate"

    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='message_reactions'
    )
    reaction_type = models.CharField(max_length=10, choices=ReactionType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user', 'reaction_type')
        indexes = [
            models.Index(fields=['message', 'reaction_type']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.reaction_type}"


class MessageReadReceipt(models.Model):
    """
    Accusés de réception des messages
    """
    message = models.ForeignKey(
        Message, 
        on_delete=models.CASCADE,
        related_name='read_receipts'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='message_read_receipts'
    )
    read_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('message', 'user')
        indexes = [
            models.Index(fields=['message', 'read_at']),
        ]

    def __str__(self):
        return f"{self.user.username} a lu le message à {self.read_at}"


class TypingIndicator(models.Model):
    """
    Indicateur de saisie en cours
    """
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE,
        related_name='typing_indicators'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='typing_in'
    )
    started_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('conversation', 'user')

    def __str__(self):
        return f"{self.user.username} est en train d'écrire..."