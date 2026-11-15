"""
G-Connect - Establishments Admin
Configuration de l'interface d'administration Django pour les établissements
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Institution, StudentInstitution, AlumniInstitution,
    Promotion, PromotionMembership, AlumniPromotionMembership,
    PromotionJoinRequest, PromotionDiscussionGroup,
    StudentAccountOrder
)


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    """Administration des établissements"""
    
    list_display = [
        'name', 'acronym', 'text_code', 'city', 'country',
        'is_active', 'members_count', 'promotions_count', 'created_at'
    ]
    list_filter = ['is_active', 'country', 'region', 'created_at']
    search_fields = ['name', 'acronym', 'text_code', 'email', 'phone']
    readonly_fields = [
        'text_code', 'qr_uuid', 'slug', 'created_at', 'updated_at',
        'qr_code_display', 'general_promotion_link'
    ]
    
    fieldsets = (
        ('Informations Principales', {
            'fields': ('name', 'acronym', 'slug', 'description')
        }),
        ('Codes d\'Accès', {
            'fields': ('text_code', 'qr_uuid', 'qr_code_display'),
            'description': 'Codes pour l\'inscription des étudiants'
        }),
        ('Localisation', {
            'fields': ('address', 'city', 'region', 'country', 'latitude', 'longitude')
        }),
        ('Contact', {
            'fields': ('phone', 'email', 'website')
        }),
        ('Médias', {
            'fields': ('logo', 'cover_image')
        }),
        ('Informations Supplémentaires', {
            'fields': ('established_year', 'accreditation', 'is_active')
        }),
        ('Promotion Générale', {
            'fields': ('general_promotion_link',),
            'description': 'Promotion générale créée automatiquement'
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_institutions', 'deactivate_institutions', 'regenerate_codes']
    
    def members_count(self, obj):
        """Compte total des membres (étudiants + alumni)"""
        students = StudentInstitution.objects.filter(institution=obj).count()
        alumni = AlumniInstitution.objects.filter(institution=obj).count()
        return f"{students + alumni} ({students}👨‍🎓 + {alumni}🎓)"
    members_count.short_description = "Membres"
    
    def promotions_count(self, obj):
        """Nombre de promotions"""
        count = obj.promotions.count()
        url = reverse('admin:establishments_promotion_changelist') + f'?institution__id__exact={obj.id}'
        return format_html('<a href="{}">{} promotions</a>', url, count)
    promotions_count.short_description = "Promotions"
    
    def qr_code_display(self, obj):
        """Affiche un aperçu du QR code"""
        if obj.qr_uuid:
            return format_html(
                '<div style="background: white; padding: 10px; display: inline-block;">'
                '<img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={}" />'
                '<p><strong>UUID:</strong> {}</p>'
                '</div>',
                obj.qr_uuid,
                obj.qr_uuid
            )
        return "QR UUID non généré"
    qr_code_display.short_description = "QR Code"
    
    def general_promotion_link(self, obj):
        """Lien vers la promotion générale"""
        promo = obj.general_promotion
        if promo:
            url = reverse('admin:establishments_promotion_change', args=[promo.pk])
            return format_html(
                '<a href="{}" style="font-weight: bold;">🎓 {} ({}  membres)</a>',
                url,
                promo.name,
                promo.members_count
            )
        return format_html('<span style="color: red;">❌ Promotion générale non créée</span>')
    general_promotion_link.short_description = "Promotion Générale"
    
    def activate_institutions(self, request, queryset):
        """Action pour activer les établissements"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} établissement(s) activé(s)")
    activate_institutions.short_description = "✅ Activer les établissements sélectionnés"
    
    def deactivate_institutions(self, request, queryset):
        """Action pour désactiver les établissements"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} établissement(s) désactivé(s)")
    deactivate_institutions.short_description = "❌ Désactiver les établissements sélectionnés"
    
    def regenerate_codes(self, request, queryset):
        """Action pour regénérer les codes d'accès"""
        for institution in queryset:
            institution.regenerate_codes()
        self.message_user(request, f"Codes régénérés pour {queryset.count()} établissement(s)")
    regenerate_codes.short_description = "🔄 Regénérer les codes d'accès"


class PromotionMembershipInline(admin.TabularInline):
    """Inline pour les membres d'une promotion"""
    model = PromotionMembership
    extra = 0
    readonly_fields = ['joined_at', 'approved_by', 'approved_at']
    fields = ['student', 'is_approved', 'is_delegate', 'joined_at', 'approved_by']
    raw_id_fields = ['student', 'approved_by']


class AlumniPromotionMembershipInline(admin.TabularInline):
    """Inline pour les alumni d'une promotion"""
    model = AlumniPromotionMembership
    extra = 0
    readonly_fields = ['joined_at', 'approved_by', 'approved_at']
    fields = ['alumni', 'is_approved', 'joined_at', 'approved_by']
    raw_id_fields = ['alumni', 'approved_by']


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    """Administration des promotions"""
    
    list_display = [
        'name', 'institution', 'promotion_type', 'year', 'department',
        'level', 'members_count', 'pending_requests', 'created_at'
    ]
    list_filter = [
        'is_general', 'institution', 'year', 'level', 'created_at'
    ]
    search_fields = ['name', 'description', 'department', 'institution__name']
    readonly_fields = ['created_at', 'updated_at', 'discussion_group_link']
    
    fieldsets = (
        ('Informations Principales', {
            'fields': ('institution', 'name', 'description', 'is_general')
        }),
        ('Détails (Promotions Spécifiques)', {
            'fields': ('year', 'department', 'level', 'cover_image'),
            'description': 'Ces champs sont utilisés pour les promotions spécifiques'
        }),
        ('Groupe de Discussion', {
            'fields': ('discussion_group_link',),
            'description': 'Groupe créé automatiquement'
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PromotionMembershipInline, AlumniPromotionMembershipInline]
    actions = ['export_members']
    
    def promotion_type(self, obj):
        """Type de promotion avec badge"""
        if obj.is_general:
            return format_html('<span style="background: #28a745; color: white; padding: 3px 8px; border-radius: 3px;">🌍 GÉNÉRALE</span>')
        return format_html('<span style="background: #007bff; color: white; padding: 3px 8px; border-radius: 3px;">🎯 SPÉCIFIQUE</span>')
    promotion_type.short_description = "Type"
    
    def pending_requests(self, obj):
        """Nombre de demandes en attente"""
        count = obj.pending_requests_count
        if count > 0:
            url = reverse('admin:establishments_promotionjoinrequest_changelist') + f'?promotion__id__exact={obj.id}&status__exact=pending'
            return format_html('<a href="{}" style="color: orange; font-weight: bold;">⏳ {} demande(s)</a>', url, count)
        return "✅ Aucune"
    pending_requests.short_description = "Demandes en attente"
    
    def discussion_group_link(self, obj):
        """Lien vers le groupe de discussion"""
        if hasattr(obj, 'discussion_group'):
            group = obj.discussion_group
            return format_html(
                '<div style="padding: 10px; background: #f0f0f0; border-radius: 5px;">'
                '<p><strong>💬 Groupe de discussion:</strong> {}</p>'
                '<p><strong>Conversation ID:</strong> {}</p>'
                '</div>',
                group.conversation.name,
                group.conversation.id
            )
        return format_html('<span style="color: red;">❌ Groupe non créé</span>')
    discussion_group_link.short_description = "Groupe de Discussion"
    
    def export_members(self, request, queryset):
        """Exporte la liste des membres"""
        # TODO: Implémenter l'export CSV/Excel
        self.message_user(request, "Fonctionnalité d'export en cours de développement")
    export_members.short_description = "📥 Exporter les membres"


@admin.register(PromotionMembership)
class PromotionMembershipAdmin(admin.ModelAdmin):
    """Administration des adhésions aux promotions (étudiants)"""
    
    list_display = [
        'student_name', 'promotion', 'status_badge', 'delegate_badge',
        'joined_at', 'approved_by_name'
    ]
    list_filter = [
        'is_approved', 'is_delegate', 'promotion__institution',
        'promotion', 'joined_at'
    ]
    search_fields = [
        'student__user__username', 'student__user__first_name',
        'student__user__last_name', 'promotion__name'
    ]
    readonly_fields = ['joined_at', 'approved_at']
    raw_id_fields = ['student', 'promotion', 'approved_by']
    
    fieldsets = (
        ('Adhésion', {
            'fields': ('student', 'promotion', 'joined_at')
        }),
        ('Statut', {
            'fields': ('is_approved', 'is_delegate')
        }),
        ('Approbation', {
            'fields': ('approved_by', 'approved_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_memberships', 'make_delegate', 'remove_delegate']
    
    def student_name(self, obj):
        """Nom de l'étudiant"""
        return obj.student.user.get_full_name() or obj.student.user.username
    student_name.short_description = "Étudiant"
    
    def status_badge(self, obj):
        """Badge de statut"""
        if obj.is_approved:
            return format_html('<span style="color: green;">✅ Approuvé</span>')
        return format_html('<span style="color: orange;">⏳ En attente</span>')
    status_badge.short_description = "Statut"
    
    def delegate_badge(self, obj):
        """Badge délégué"""
        if obj.is_delegate:
            return format_html('<span style="background: gold; color: black; padding: 2px 6px; border-radius: 3px;">⭐ DÉLÉGUÉ</span>')
        return "-"
    delegate_badge.short_description = "Délégué"
    
    def approved_by_name(self, obj):
        """Nom de l'approbateur"""
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return "-"
    approved_by_name.short_description = "Approuvé par"
    
    def approve_memberships(self, request, queryset):
        """Action pour approuver les adhésions"""
        for membership in queryset:
            membership.approve(request.user)
        self.message_user(request, f"{queryset.count()} adhésion(s) approuvée(s)")
    approve_memberships.short_description = "✅ Approuver les adhésions"
    
    def make_delegate(self, request, queryset):
        """Action pour nommer délégué"""
        queryset.update(is_delegate=True)
        self.message_user(request, f"{queryset.count()} membre(s) nommé(s) délégué(s)")
    make_delegate.short_description = "⭐ Nommer délégué(s)"
    
    def remove_delegate(self, request, queryset):
        """Action pour retirer le statut de délégué"""
        queryset.update(is_delegate=False)
        self.message_user(request, f"Statut de délégué retiré pour {queryset.count()} membre(s)")
    remove_delegate.short_description = "❌ Retirer statut délégué"


@admin.register(AlumniPromotionMembership)
class AlumniPromotionMembershipAdmin(admin.ModelAdmin):
    """Administration des adhésions aux promotions (alumni)"""
    
    list_display = [
        'alumni_name', 'promotion', 'status_badge',
        'joined_at', 'approved_by_name'
    ]
    list_filter = [
        'is_approved', 'promotion__institution',
        'promotion', 'joined_at'
    ]
    search_fields = [
        'alumni__user__username', 'alumni__user__first_name',
        'alumni__user__last_name', 'promotion__name'
    ]
    readonly_fields = ['joined_at', 'approved_at']
    raw_id_fields = ['alumni', 'promotion', 'approved_by']
    
    actions = ['approve_memberships']
    
    def alumni_name(self, obj):
        """Nom de l'alumni"""
        return obj.alumni.user.get_full_name() or obj.alumni.user.username
    alumni_name.short_description = "Alumni"
    
    def status_badge(self, obj):
        """Badge de statut"""
        if obj.is_approved:
            return format_html('<span style="color: green;">✅ Approuvé</span>')
        return format_html('<span style="color: orange;">⏳ En attente</span>')
    status_badge.short_description = "Statut"
    
    def approved_by_name(self, obj):
        """Nom de l'approbateur"""
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return "-"
    approved_by_name.short_description = "Approuvé par"
    
    def approve_memberships(self, request, queryset):
        """Action pour approuver les adhésions"""
        for membership in queryset:
            membership.approve(request.user)
        self.message_user(request, f"{queryset.count()} adhésion(s) approuvée(s)")
    approve_memberships.short_description = "✅ Approuver les adhésions"


@admin.register(PromotionJoinRequest)
class PromotionJoinRequestAdmin(admin.ModelAdmin):
    """Administration des demandes d'adhésion"""
    
    list_display = [
        'requester_name', 'promotion', 'status_badge',
        'created_at', 'processed_by_name', 'processed_at'
    ]
    list_filter = [
        'status', 'promotion__institution', 'promotion', 'created_at'
    ]
    search_fields = [
        'student__user__username', 'student__user__first_name',
        'student__user__last_name', 'alumni__user__username',
        'alumni__user__first_name', 'alumni__user__last_name',
        'promotion__name', 'motivation'
    ]
    readonly_fields = ['created_at', 'processed_at']
    raw_id_fields = ['student', 'alumni', 'promotion', 'processed_by']
    
    fieldsets = (
        ('Demande', {
            'fields': ('student', 'alumni', 'promotion', 'motivation', 'created_at')
        }),
        ('Traitement', {
            'fields': ('status', 'processed_by', 'processed_at', 'rejection_reason')
        }),
    )
    
    actions = ['accept_requests', 'reject_requests']
    
    def requester_name(self, obj):
        """Nom du demandeur"""
        user = obj.student.user if obj.student else obj.alumni.user
        return user.get_full_name() or user.username
    requester_name.short_description = "Demandeur"
    
    def status_badge(self, obj):
        """Badge de statut avec couleur"""
        colors = {
            'pending': ('orange', '⏳ En attente'),
            'accepted': ('green', '✅ Acceptée'),
            'rejected': ('red', '❌ Rejetée'),
        }
        color, text = colors.get(obj.status, ('gray', obj.status))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, text
        )
    status_badge.short_description = "Statut"
    
    def processed_by_name(self, obj):
        """Nom du validateur"""
        if obj.processed_by:
            return obj.processed_by.get_full_name() or obj.processed_by.username
        return "-"
    processed_by_name.short_description = "Traité par"
    
    def accept_requests(self, request, queryset):
        """Action pour accepter les demandes"""
        accepted = 0
        for join_request in queryset.filter(status='pending'):
            try:
                if join_request.can_be_approved_by(request.user):
                    join_request.accept(request.user)
                    accepted += 1
            except Exception as e:
                self.message_user(request, f"Erreur: {str(e)}", level='error')
        
        self.message_user(request, f"{accepted} demande(s) acceptée(s)")
    accept_requests.short_description = "✅ Accepter les demandes"
    
    def reject_requests(self, request, queryset):
        """Action pour rejeter les demandes"""
        rejected = 0
        for join_request in queryset.filter(status='pending'):
            try:
                if join_request.can_be_approved_by(request.user):
                    join_request.reject(request.user, reason="Rejet administratif")
                    rejected += 1
            except Exception as e:
                self.message_user(request, f"Erreur: {str(e)}", level='error')
        
        self.message_user(request, f"{rejected} demande(s) rejetée(s)")
    reject_requests.short_description = "❌ Rejeter les demandes"


@admin.register(PromotionDiscussionGroup)
class PromotionDiscussionGroupAdmin(admin.ModelAdmin):
    """Administration des groupes de discussion"""
    
    list_display = ['promotion', 'conversation_name', 'created_at']
    list_filter = ['promotion__institution', 'created_at']
    search_fields = ['promotion__name', 'conversation__name']
    readonly_fields = ['created_at', 'conversation_details']
    raw_id_fields = ['promotion', 'conversation']
    
    fieldsets = (
        ('Groupe', {
            'fields': ('promotion', 'conversation', 'created_at')
        }),
        ('Détails de la Conversation', {
            'fields': ('conversation_details',),
            'classes': ('collapse',)
        }),
    )
    
    def conversation_name(self, obj):
        """Nom de la conversation"""
        return obj.conversation.name
    conversation_name.short_description = "Nom du groupe"
    
    def conversation_details(self, obj):
        """Détails de la conversation"""
        conv = obj.conversation
        participants_count = conv.participants.count()
        messages_count = conv.messages.count()
        
        return format_html(
            '<div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">'
            '<h3>📊 Statistiques</h3>'
            '<p><strong>Participants:</strong> {}</p>'
            '<p><strong>Messages:</strong> {}</p>'
            '<p><strong>Dernier message:</strong> {}</p>'
            '<p><strong>Type:</strong> {}</p>'
            '</div>',
            participants_count,
            messages_count,
            conv.last_message_at or 'Aucun',
            conv.get_conversation_type_display()
        )
    conversation_details.short_description = "Détails"


@admin.register(StudentInstitution)
class StudentInstitutionAdmin(admin.ModelAdmin):
    """Administration des liens étudiant-établissement"""
    
    list_display = ['student_name', 'institution', 'is_primary', 'joined_at']
    list_filter = ['is_primary', 'institution', 'joined_at']
    search_fields = [
        'student__user__username', 'student__user__first_name',
        'student__user__last_name', 'institution__name'
    ]
    readonly_fields = ['joined_at']
    raw_id_fields = ['student', 'institution']
    
    def student_name(self, obj):
        """Nom de l'étudiant"""
        return obj.student.user.get_full_name() or obj.student.user.username
    student_name.short_description = "Étudiant"


@admin.register(AlumniInstitution)
class AlumniInstitutionAdmin(admin.ModelAdmin):
    """Administration des liens alumni-établissement"""
    
    list_display = ['alumni_name', 'institution', 'joined_at']
    list_filter = ['institution', 'joined_at']
    search_fields = [
        'alumni__user__username', 'alumni__user__first_name',
        'alumni__user__last_name', 'institution__name'
    ]
    readonly_fields = ['joined_at']
    raw_id_fields = ['alumni', 'institution']
    
    def alumni_name(self, obj):
        """Nom de l'alumni"""
        return obj.alumni.user.get_full_name() or obj.alumni.user.username
    alumni_name.short_description = "Alumni"


@admin.register(StudentAccountOrder)
class StudentAccountOrderAdmin(admin.ModelAdmin):
    """Administration des commandes de comptes"""
    
    list_display = [
        'id', 'institution', 'year', 'quantity', 'status_badge',
        'remaining_display', 'total_price_display', 'created_at'
    ]
    list_filter = ['status', 'year', 'institution', 'created_at']
    search_fields = ['institution__name']
    readonly_fields = ['created_at', 'total_price', 'remaining']
    
    fieldsets = (
        ('Commande', {
            'fields': ('institution', 'year', 'quantity', 'price_per_account')
        }),
        ('Statut', {
            'fields': ('status', 'used_accounts')
        }),
        ('Résumé', {
            'fields': ('total_price', 'remaining', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_orders', 'reject_orders']
    
    def status_badge(self, obj):
        """Badge de statut"""
        colors = {
            'pending': ('orange', '⏳ En attente'),
            'approved': ('green', '✅ Approuvée'),
            'rejected': ('red', '❌ Rejetée'),
        }
        color, text = colors.get(obj.status, ('gray', obj.status))
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, text
        )
    status_badge.short_description = "Statut"
    
    def remaining_display(self, obj):
        """Affichage du reste"""
        remaining = obj.remaining
        used = obj.used_accounts
        total = obj.quantity
        percentage = (used / total * 100) if total > 0 else 0
        
        color = 'green' if percentage < 50 else 'orange' if percentage < 80 else 'red'
        
        return format_html(
            '<div style="color: {};">{} / {} ({}%)</div>',
            color, remaining, total, round(percentage)
        )
    remaining_display.short_description = "Disponibles"
    
    def approve_orders(self, request, queryset):
        """Action pour approuver les commandes"""
        updated = queryset.filter(status='pending').update(status='approved')
        self.message_user(request, f"{updated} commande(s) approuvée(s)")
    approve_orders.short_description = "✅ Approuver les commandes"
    
    def reject_orders(self, request, queryset):
        """Action pour rejeter les commandes"""
        updated = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f"{updated} commande(s) rejetée(s)")
    reject_orders.short_description = "❌ Rejeter les commandes"