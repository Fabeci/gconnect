"""
G-Connect - Messaging Admin
Interface d'administration pour l'application de messagerie
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q

from apps.api.v1.messaging.models import (
    Conversation, ConversationParticipant, Message, MessageAttachment,
    MessageReaction, MessageReadReceipt, TypingIndicator
)


# ==================== INLINES ====================

class ConversationParticipantInline(admin.TabularInline):
    """Inline pour les participants d'une conversation"""
    model = ConversationParticipant
    extra = 0
    fields = ['user', 'role', 'is_online', 'last_seen', 'unread_count', 'is_muted', 'is_active']
    readonly_fields = ['last_seen', 'unread_count']
    autocomplete_fields = ['user']


class MessageAttachmentInline(admin.TabularInline):
    """Inline pour les pièces jointes"""
    model = MessageAttachment
    extra = 0
    fields = ['file', 'file_name', 'file_size_display', 'uploaded_at']
    readonly_fields = ['file_size_display', 'uploaded_at']
    
    def file_size_display(self, obj):
        """Affiche la taille formatée"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    file_size_display.short_description = "Taille"


class MessageReactionInline(admin.TabularInline):
    """Inline pour les réactions"""
    model = MessageReaction
    extra = 0
    fields = ['user', 'reaction_type', 'created_at']
    readonly_fields = ['created_at']
    autocomplete_fields = ['user']


# ==================== ADMIN CLASSES ====================

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """Admin pour les conversations"""
    list_display = [
        'id', 'conversation_type_display', 'name_display', 
        'participants_count', 'messages_count', 'last_message_display',
        'created_at', 'is_archived_display'
    ]
    list_filter = ['conversation_type', 'is_archived', 'created_at']
    search_fields = ['name', 'participants__username', 'participants__email']
    readonly_fields = ['created_at', 'updated_at', 'last_message_at', 'statistics_dashboard']
    autocomplete_fields = ['created_by']
    inlines = [ConversationParticipantInline]
    
    fieldsets = (
        ('📋 Informations générales', {
            'fields': ('conversation_type', 'name', 'description', 'created_by')
        }),
        ('🖼️ Média', {
            'fields': ('group_photo',),
            'classes': ('collapse',)
        }),
        ('📊 Statistiques', {
            'fields': ('statistics_dashboard',)
        }),
        ('🕐 Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_message_at'),
            'classes': ('collapse',)
        }),
        ('🗄️ Gestion', {
            'fields': ('is_archived',)
        }),
    )
    
    def conversation_type_display(self, obj):
        """Type avec emoji"""
        if obj.conversation_type == 'direct':
            return format_html(
                '<span style="color: #007bff;">💬 Direct</span>'
            )
        return format_html(
            '<span style="color: #28a745;">👥 Groupe</span>'
        )
    conversation_type_display.short_description = "Type"
    
    def name_display(self, obj):
        """Nom formaté"""
        if obj.conversation_type == 'group':
            return obj.name or f"Groupe #{obj.id}"
        
        # Pour conversations directes, afficher les participants
        participants = obj.participants.all()[:2]
        if participants:
            names = " ↔️ ".join([p.username for p in participants])
            return format_html('<span style="color: #6c757d;">{}</span>', names)
        return f"Conversation #{obj.id}"
    name_display.short_description = "Nom"
    
    def participants_count(self, obj):
        """Nombre de participants"""
        count = obj.memberships.filter(is_active=True).count()
        return format_html(
            '<span style="background: #e9ecef; padding: 3px 8px; border-radius: 3px; font-weight: bold;">'
            '👥 {}</span>',
            count
        )
    participants_count.short_description = "Participants"
    
    def messages_count(self, obj):
        """Nombre de messages"""
        count = obj.messages.filter(is_deleted=False).count()
        color = '#28a745' if count > 100 else '#6c757d'
        return format_html(
            '<span style="color: {}; font-weight: bold;">💬 {}</span>',
            color, count
        )
    messages_count.short_description = "Messages"
    
    def last_message_display(self, obj):
        """Dernier message"""
        last_msg = obj.messages.filter(is_deleted=False).order_by('-created_at').first()
        if not last_msg:
            return format_html('<span style="color: #999;">Aucun message</span>')
        
        content = last_msg.content[:30] + "..." if len(last_msg.content) > 30 else last_msg.content
        return format_html(
            '<div style="font-size: 11px;">'
            '<strong>{}</strong><br>'
            '<span style="color: #666;">{}</span>'
            '</div>',
            last_msg.sender.username if last_msg.sender else "Système",
            content
        )
    last_message_display.short_description = "Dernier message"
    
    def is_archived_display(self, obj):
        """Statut archivage"""
        if obj.is_archived:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">📦 Archivé</span>'
            )
        return format_html(
            '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">✅ Actif</span>'
        )
    is_archived_display.short_description = "Statut"
    
    def statistics_dashboard(self, obj):
        """Dashboard de statistiques"""
        total_messages = obj.messages.filter(is_deleted=False).count()
        total_participants = obj.memberships.filter(is_active=True).count()
        active_participants = obj.memberships.filter(is_active=True, is_online=True).count()
        
        # Répartition des types de messages
        text_count = obj.messages.filter(message_type='text', is_deleted=False).count()
        image_count = obj.messages.filter(message_type='image', is_deleted=False).count()
        file_count = obj.messages.filter(message_type='file', is_deleted=False).count()
        
        html = f"""
        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px;">
            <h3 style="margin-top: 0;">📊 Statistiques de la conversation</h3>
            
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 15px;">
                <div style="background: white; padding: 10px; border-radius: 5px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #007bff;">{total_messages}</div>
                    <div style="color: #666; font-size: 12px;">Messages totaux</div>
                </div>
                <div style="background: white; padding: 10px; border-radius: 5px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #28a745;">{total_participants}</div>
                    <div style="color: #666; font-size: 12px;">Participants</div>
                </div>
                <div style="background: white; padding: 10px; border-radius: 5px; text-align: center;">
                    <div style="font-size: 24px; font-weight: bold; color: #17a2b8;">{active_participants}</div>
                    <div style="color: #666; font-size: 12px;">En ligne</div>
                </div>
            </div>
            
            <h4>📝 Types de messages</h4>
            <div style="background: white; padding: 10px; border-radius: 5px;">
                <div style="margin: 5px 0;">💬 Texte : <strong>{text_count}</strong></div>
                <div style="margin: 5px 0;">🖼️ Images : <strong>{image_count}</strong></div>
                <div style="margin: 5px 0;">📎 Fichiers : <strong>{file_count}</strong></div>
            </div>
        </div>
        """
        return mark_safe(html)
    statistics_dashboard.short_description = "Statistiques"
    
    def get_queryset(self, request):
        """Optimise les requêtes"""
        return super().get_queryset(request).select_related(
            'created_by'
        ).prefetch_related('participants', 'memberships')


@admin.register(ConversationParticipant)
class ConversationParticipantAdmin(admin.ModelAdmin):
    """Admin pour les participants"""
    list_display = [
        'user_display', 'conversation_display', 'role_display',
        'status_display', 'unread_count_display', 'last_seen_display',
        'joined_at'
    ]
    list_filter = ['role', 'is_active', 'is_online', 'is_muted', 'joined_at']
    search_fields = ['user__username', 'user__email', 'conversation__name']
    readonly_fields = ['joined_at', 'last_seen', 'left_at']
    autocomplete_fields = ['user', 'conversation']
    
    fieldsets = (
        ('👤 Participant', {
            'fields': ('user', 'conversation', 'role')
        }),
        ('📊 Statut', {
            'fields': ('is_online', 'last_seen', 'is_active', 'left_at')
        }),
        ('📬 Messages', {
            'fields': ('last_read_at', 'unread_count')
        }),
        ('🔔 Notifications', {
            'fields': ('notifications_enabled', 'is_muted', 'muted_until')
        }),
        ('🕐 Timestamps', {
            'fields': ('joined_at',)
        }),
    )
    
    def user_display(self, obj):
        """Utilisateur avec statut en ligne"""
        status = "🟢" if obj.is_online else "⚪"
        return format_html(
            '{} <strong>{}</strong>',
            status, obj.user.username
        )
    user_display.short_description = "Utilisateur"
    
    def conversation_display(self, obj):
        """Conversation formatée"""
        if obj.conversation.conversation_type == 'group':
            name = obj.conversation.name or f"Groupe #{obj.conversation.id}"
            return format_html(
                '<span style="color: #28a745;">👥 {}</span>',
                name
            )
        return format_html(
            '<span style="color: #007bff;">💬 Conversation #{}</span>',
            obj.conversation.id
        )
    conversation_display.short_description = "Conversation"
    
    def role_display(self, obj):
        """Rôle avec badge"""
        if obj.role == 'admin':
            return format_html(
                '<span style="background: #ffc107; color: #000; padding: 3px 8px; border-radius: 3px; font-weight: bold;">⭐ ADMIN</span>'
            )
        return format_html(
            '<span style="background: #e9ecef; padding: 3px 8px; border-radius: 3px;">👤 Membre</span>'
        )
    role_display.short_description = "Rôle"
    
    def status_display(self, obj):
        """Statut d'activité"""
        if not obj.is_active:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">❌ Inactif</span>'
            )
        if obj.is_muted:
            return format_html(
                '<span style="background: #6c757d; color: white; padding: 3px 8px; border-radius: 3px;">🔇 En sourdine</span>'
            )
        return format_html(
            '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">✅ Actif</span>'
        )
    status_display.short_description = "Statut"
    
    def unread_count_display(self, obj):
        """Messages non lus avec couleur"""
        if obj.unread_count == 0:
            return format_html('<span style="color: #999;">0</span>')
        
        color = '#dc3545' if obj.unread_count > 10 else '#ffc107'
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 10px; font-weight: bold;">{}</span>',
            color, obj.unread_count
        )
    unread_count_display.short_description = "Non lus"
    
    def last_seen_display(self, obj):
        """Dernière activité"""
        if not obj.last_seen:
            return format_html('<span style="color: #999;">Jamais</span>')
        
        from django.utils import timezone
        diff = timezone.now() - obj.last_seen
        
        if diff.total_seconds() < 300:  # 5 minutes
            return format_html('<span style="color: #28a745; font-weight: bold;">🟢 En ligne</span>')
        elif diff.days == 0:
            hours = int(diff.total_seconds() // 3600)
            return format_html('<span style="color: #666;">Il y a {}h</span>', hours)
        else:
            return format_html('<span style="color: #999;">Il y a {} jour(s)</span>', diff.days)
    last_seen_display.short_description = "Dernière activité"


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin pour les messages"""
    list_display = [
        'id', 'sender_display', 'conversation_link', 'message_type_display',
        'content_preview', 'attachments_count', 'reactions_count',
        'status_display', 'created_at'
    ]
    list_filter = ['message_type', 'is_deleted', 'is_edited', 'created_at']
    search_fields = ['content', 'sender__username', 'conversation__name']
    readonly_fields = ['created_at', 'edited_at', 'deleted_at', 'delivered_at', 'engagement_stats']
    autocomplete_fields = ['sender', 'conversation', 'reply_to']
    inlines = [MessageAttachmentInline, MessageReactionInline]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('💬 Message', {
            'fields': ('conversation', 'sender', 'message_type', 'content', 'reply_to')
        }),
        ('📊 Engagement', {
            'fields': ('engagement_stats',)
        }),
        ('🕐 Timestamps', {
            'fields': ('created_at', 'edited_at', 'delivered_at'),
            'classes': ('collapse',)
        }),
        ('🗑️ Suppression', {
            'fields': ('is_deleted', 'deleted_at'),
            'classes': ('collapse',)
        }),
    )
    
    def sender_display(self, obj):
        """Expéditeur formaté"""
        if not obj.sender:
            return format_html('<span style="color: #6c757d;">⚙️ Système</span>')
        
        return format_html(
            '<strong>{}</strong>',
            obj.sender.username
        )
    sender_display.short_description = "Expéditeur"
    
    def conversation_link(self, obj):
        """Lien vers la conversation"""
        url = reverse('admin:messaging_conversation_change', args=[obj.conversation.id])
        name = obj.conversation.name or f"Conv #{obj.conversation.id}"
        return format_html(
            '<a href="{}" style="color: #007bff;">💬 {}</a>',
            url, name
        )
    conversation_link.short_description = "Conversation"
    
    def message_type_display(self, obj):
        """Type avec emoji"""
        types = {
            'text': ('💬', '#007bff'),
            'image': ('🖼️', '#28a745'),
            'video': ('🎥', '#dc3545'),
            'audio': ('🎵', '#6f42c1'),
            'file': ('📎', '#fd7e14'),
            'voice': ('🎤', '#17a2b8'),
            'system': ('⚙️', '#6c757d'),
        }
        emoji, color = types.get(obj.message_type, ('📝', '#000'))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}</span>',
            color, emoji, obj.get_message_type_display()
        )
    message_type_display.short_description = "Type"
    
    def content_preview(self, obj):
        """Aperçu du contenu"""
        if obj.is_deleted:
            return format_html('<span style="color: #dc3545; font-style: italic;">🗑️ Message supprimé</span>')
        
        if not obj.content:
            return format_html('<span style="color: #999;">(pas de texte)</span>')
        
        preview = obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
        return format_html('<span>{}</span>', preview)
    content_preview.short_description = "Contenu"
    
    def attachments_count(self, obj):
        """Nombre de pièces jointes"""
        count = obj.attachments.count()
        if count == 0:
            return format_html('<span style="color: #999;">-</span>')
        
        return format_html(
            '<span style="background: #e9ecef; padding: 3px 8px; border-radius: 3px;">📎 {}</span>',
            count
        )
    attachments_count.short_description = "Fichiers"
    
    def reactions_count(self, obj):
        """Nombre de réactions"""
        count = obj.reactions.count()
        if count == 0:
            return format_html('<span style="color: #999;">-</span>')
        
        return format_html(
            '<span style="background: #fff3cd; padding: 3px 8px; border-radius: 3px;">❤️ {}</span>',
            count
        )
    reactions_count.short_description = "Réactions"
    
    def status_display(self, obj):
        """Statut du message"""
        if obj.is_deleted:
            return format_html(
                '<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px;">🗑️ Supprimé</span>'
            )
        if obj.is_edited:
            return format_html(
                '<span style="background: #ffc107; color: #000; padding: 3px 8px; border-radius: 3px;">✏️ Édité</span>'
            )
        return format_html(
            '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">✅ OK</span>'
        )
    status_display.short_description = "Statut"
    
    def engagement_stats(self, obj):
        """Statistiques d'engagement"""
        reactions = obj.reactions.count()
        read_receipts = obj.read_receipts.count()
        attachments = obj.attachments.count()
        
        html = f"""
        <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
            <div style="margin: 5px 0;">❤️ Réactions : <strong>{reactions}</strong></div>
            <div style="margin: 5px 0;">👁️ Lectures : <strong>{read_receipts}</strong></div>
            <div style="margin: 5px 0;">📎 Pièces jointes : <strong>{attachments}</strong></div>
        </div>
        """
        return mark_safe(html)
    engagement_stats.short_description = "Statistiques"
    
    def get_queryset(self, request):
        """Optimise les requêtes"""
        return super().get_queryset(request).select_related(
            'sender', 'conversation', 'reply_to'
        ).prefetch_related('attachments', 'reactions')


@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    """Admin pour les pièces jointes"""
    list_display = [
        'id', 'message_link', 'file_name',
        'file_size_display', 'dimensions', 'uploaded_at'
    ]
    list_filter = ['uploaded_at']
    search_fields = ['file_name', 'message__content']
    readonly_fields = ['uploaded_at', 'file_preview']
    autocomplete_fields = ['message']
    
    fieldsets = (
        ('📎 Fichier', {
            'fields': ('message', 'file', 'file_name', 'mime_type')
        }),
        ('📊 Métadonnées', {
            'fields': ('file_size', 'width', 'height', 'duration')
        }),
        ('🖼️ Aperçu', {
            'fields': ('file_preview', 'thumbnail')
        }),
        ('🕐 Date', {
            'fields': ('uploaded_at',)
        }),
    )
    
    def message_link(self, obj):
        """Lien vers le message"""
        url = reverse('admin:messaging_message_change', args=[obj.message.id])
        return format_html(
            '<a href="{}" style="color: #007bff;">💬 Message #{}</a>',
            url, obj.message.id
        )
    message_link.short_description = "Message"
    
    def file_size_display(self, obj):
        """Taille formatée"""
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return format_html(
                    '<span style="font-weight: bold;">{:.1f} {}</span>',
                    size, unit
                )
            size /= 1024.0
        return format_html('<span>{:.1f} TB</span>', size)
    file_size_display.short_description = "Taille"
    
    def dimensions(self, obj):
        """Dimensions ou durée"""
        if obj.width and obj.height:
            return format_html('{}x{}', obj.width, obj.height)
        if obj.duration:
            minutes = obj.duration // 60
            seconds = obj.duration % 60
            return format_html('{}:{:02d}', minutes, seconds)
        return "-"
    dimensions.short_description = "Dimensions/Durée"
    
    def file_preview(self, obj):
        """Aperçu du fichier"""
        # Vérifier si c'est une image par le mime_type
        if obj.mime_type and obj.mime_type.startswith('image/') and obj.file:
            return format_html(
                '<img src="{}" style="max-width: 300px; max-height: 300px; border-radius: 5px;" />',
                obj.file.url
            )
        return format_html('<span style="color: #999;">Pas d\'aperçu disponible</span>')
    file_preview.short_description = "Aperçu"


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    """Admin pour les réactions"""
    list_display = ['user', 'message_link', 'reaction_display', 'created_at']
    list_filter = ['reaction_type', 'created_at']
    search_fields = ['user__username', 'message__content']
    readonly_fields = ['created_at']
    autocomplete_fields = ['user', 'message']
    
    def message_link(self, obj):
        """Lien vers le message"""
        url = reverse('admin:messaging_message_change', args=[obj.message.id])
        preview = obj.message.content[:30] + "..." if len(obj.message.content) > 30 else obj.message.content
        return format_html(
            '<a href="{}" style="color: #007bff;">{}</a>',
            url, preview
        )
    message_link.short_description = "Message"
    
    def reaction_display(self, obj):
        """Réaction avec emoji"""
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
        emoji = emojis.get(obj.reaction_type, '👍')
        return format_html(
            '<span style="font-size: 20px;">{}</span>',
            emoji
        )
    reaction_display.short_description = "Réaction"


@admin.register(MessageReadReceipt)
class MessageReadReceiptAdmin(admin.ModelAdmin):
    """Admin pour les accusés de lecture"""
    list_display = ['user', 'message_preview', 'read_at']
    list_filter = ['read_at']
    search_fields = ['user__username', 'message__content']
    readonly_fields = ['read_at']
    autocomplete_fields = ['user', 'message']
    
    def message_preview(self, obj):
        """Aperçu du message"""
        preview = obj.message.content[:40] + "..." if len(obj.message.content) > 40 else obj.message.content
        return preview
    message_preview.short_description = "Message"


@admin.register(TypingIndicator)
class TypingIndicatorAdmin(admin.ModelAdmin):
    """Admin pour les indicateurs de saisie"""
    list_display = ['user', 'conversation', 'started_at', 'is_recent']
    list_filter = ['started_at']
    search_fields = ['user__username', 'conversation__name']
    readonly_fields = ['started_at']
    autocomplete_fields = ['user', 'conversation']
    
    def is_recent(self, obj):
        """Vérifie si l'indicateur est récent"""
        from django.utils import timezone
        from datetime import timedelta
        
        if timezone.now() - obj.started_at < timedelta(seconds=10):
            return format_html(
                '<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">✅ Actif</span>'
            )
        return format_html(
            '<span style="background: #6c757d; color: white; padding: 3px 8px; border-radius: 3px;">⏸️ Expiré</span>'
        )
    is_recent.short_description = "Statut"