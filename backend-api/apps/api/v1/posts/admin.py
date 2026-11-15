"""
G-Connect - Posts Admin
Configuration de l'interface d'administration Django pour les publications
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.db.models import Count, Q
from .models import (
    Post, PostAttachment, Opportunity, Event, Project,
    Reaction, Comment, Share, Bookmark, Application, RSVP
)


class PostAttachmentInline(admin.TabularInline):
    """Inline pour les pièces jointes"""
    model = PostAttachment
    extra = 1
    fields = ['file', 'kind', 'alt_text', 'order']


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Administration des publications"""
    
    list_display = [
        'title', 'author_name', 'post_type_badge', 'audience_badge',
        'institution', 'engagement_stats', 'is_pinned', 'is_archived',
        'created_at'
    ]
    list_filter = [
        'post_type', 'audience', 'is_pinned', 'is_archived',
        'institution', 'created_at'
    ]
    search_fields = ['title', 'content', 'author__username', 'author__first_name', 'author__last_name']
    readonly_fields = [
        'created_at', 'updated_at', 'reactions_count', 'comments_count',
        'shares_count', 'views_count', 'engagement_display'
    ]
    filter_horizontal = ['promotion_targets']
    raw_id_fields = ['author', 'institution']
    
    fieldsets = (
        ('Publication', {
            'fields': ('author', 'institution', 'title', 'content')
        }),
        ('Type & Audience', {
            'fields': ('post_type', 'audience', 'promotion_targets'),
            'description': 'Pour audience "Promotion(s) spécifique(s)", sélectionnez les promotions cibles'
        }),
        ('Gestion', {
            'fields': ('is_pinned', 'is_archived')
        }),
        ('Statistiques', {
            'fields': ('engagement_display', 'reactions_count', 'comments_count', 'shares_count', 'views_count'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [PostAttachmentInline]
    actions = ['pin_posts', 'unpin_posts', 'archive_posts', 'unarchive_posts']
    
    def author_name(self, obj):
        """Nom de l'auteur avec rôle"""
        user = obj.author
        name = user.get_full_name() or user.username
        role_badges = {
            'student': '👨‍🎓',
            'alumni': '🎓',
            'etablissement': '🏛️',
            'enterprise': '🏢',
            'superAdmin': '⚡'
        }
        badge = role_badges.get(user.role, '👤')
        return format_html('{} {}', badge, name)
    author_name.short_description = "Auteur"
    
    def post_type_badge(self, obj):
        """Badge du type de post"""
        colors = {
            'opportunity': ('#28a745', '💼 Opportunité'),
            'event': ('#007bff', '📅 Événement'),
            'project': ('#6f42c1', '🚀 Projet'),
            'discussion': ('#6c757d', '💬 Discussion'),
            'share': ('#17a2b8', '🔄 Partage'),
        }
        color, text = colors.get(obj.post_type, ('#000', obj.post_type))
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, text
        )
    post_type_badge.short_description = "Type"
    
    def audience_badge(self, obj):
        """Badge de l'audience"""
        badges = {
            'public': ('🌍', 'Public', '#17a2b8'),
            'general_promotion': ('🏛️', 'Promotion générale', '#ffc107'),
            'specific_promotion': ('🎯', 'Promotion(s) spécifique(s)', '#dc3545'),
        }
        icon, text, color = badges.get(obj.audience, ('', obj.audience, '#6c757d'))
        
        # Ajouter le nombre de promotions cibles si applicable
        extra = ''
        if obj.audience == 'specific_promotion':
            count = obj.promotion_targets.count()
            extra = f' ({count})'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} {}{}</span>',
            color, icon, text, extra
        )
    audience_badge.short_description = "Audience"
    
    def engagement_stats(self, obj):
        """Statistiques d'engagement compactes"""
        return format_html(
            '<div style="font-size: 11px;">'
            '👁️ {} | ❤️ {} | 💬 {} | 🔄 {}'
            '</div>',
            obj.views_count,
            obj.reactions_count,
            obj.comments_count,
            obj.shares_count
        )
    engagement_stats.short_description = "Engagement"
    
    def engagement_display(self, obj):
        """Affichage détaillé de l'engagement"""
        total_engagement = obj.reactions_count + obj.comments_count + obj.shares_count
        engagement_rate = (total_engagement / obj.views_count * 100) if obj.views_count > 0 else 0
        
        return format_html(
            '<div style="padding: 15px; background: #f8f9fa; border-radius: 5px;">'
            '<h3>📊 Statistiques d\'engagement</h3>'
            '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-top: 10px;">'
            '<div style="background: white; padding: 10px; border-radius: 3px;">'
            '<strong>👁️ Vues</strong><br/><span style="font-size: 24px;">{}</span>'
            '</div>'
            '<div style="background: white; padding: 10px; border-radius: 3px;">'
            '<strong>❤️ Réactions</strong><br/><span style="font-size: 24px;">{}</span>'
            '</div>'
            '<div style="background: white; padding: 10px; border-radius: 3px;">'
            '<strong>💬 Commentaires</strong><br/><span style="font-size: 24px;">{}</span>'
            '</div>'
            '<div style="background: white; padding: 10px; border-radius: 3px;">'
            '<strong>🔄 Partages</strong><br/><span style="font-size: 24px;">{}</span>'
            '</div>'
            '</div>'
            '<p style="margin-top: 10px;"><strong>Taux d\'engagement:</strong> {:.1f}%</p>'
            '</div>',
            obj.views_count,
            obj.reactions_count,
            obj.comments_count,
            obj.shares_count,
            engagement_rate
        )
    engagement_display.short_description = "Engagement Détaillé"
    
    def pin_posts(self, request, queryset):
        """Action pour épingler"""
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f"{updated} publication(s) épinglée(s)")
    pin_posts.short_description = "📌 Épingler les publications"
    
    def unpin_posts(self, request, queryset):
        """Action pour désépingler"""
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f"{updated} publication(s) désépinglée(s)")
    unpin_posts.short_description = "📍 Désépingler les publications"
    
    def archive_posts(self, request, queryset):
        """Action pour archiver"""
        updated = queryset.update(is_archived=True)
        self.message_user(request, f"{updated} publication(s) archivée(s)")
    archive_posts.short_description = "📦 Archiver les publications"
    
    def unarchive_posts(self, request, queryset):
        """Action pour désarchiver"""
        updated = queryset.update(is_archived=False)
        self.message_user(request, f"{updated} publication(s) désarchivée(s)")
    unarchive_posts.short_description = "📂 Désarchiver les publications"


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    """Administration des opportunités"""
    
    list_display = [
        'title', 'category_badge', 'enterprise_name', 'location',
        'status_badge', 'applications_count', 'deadline', 'created_at'
    ]
    list_filter = [
        'category', 'status', 'work_mode', 'contract_type',
        'post__institution', 'deadline'
    ]
    search_fields = [
        'post__title', 'post__content', 'enterprise__company_name',
        'location_city', 'location_country'
    ]
    readonly_fields = ['created_at', 'is_expired', 'applications_stats']
    raw_id_fields = ['post', 'enterprise']
    
    fieldsets = (
        ('Publication', {
            'fields': ('post',)
        }),
        ('Opportunité', {
            'fields': ('category', 'enterprise', 'status')
        }),
        ('Localisation & Mode', {
            'fields': ('location_city', 'location_country', 'work_mode')
        }),
        ('Contrat & Durée', {
            'fields': ('contract_type', 'duration_months', 'start_date')
        }),
        ('Rémunération', {
            'fields': ('salary_min', 'salary_max', 'currency'),
            'classes': ('collapse',)
        }),
        ('Candidature', {
            'fields': ('application_url', 'application_email', 'deadline', 'is_expired')
        }),
        ('Compétences & Tags', {
            'fields': ('required_skills', 'tags'),
            'classes': ('collapse',)
        }),
        ('Statistiques', {
            'fields': ('applications_stats',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['close_opportunities', 'reopen_opportunities']
    
    def title(self, obj):
        """Titre de la publication"""
        return obj.post.title
    title.short_description = "Titre"
    
    def created_at(self, obj):
        """Date de création"""
        return obj.post.created_at
    created_at.short_description = "Créée le"
    
    def category_badge(self, obj):
        """Badge de catégorie"""
        colors = {
            'job': ('#28a745', '💼 Emploi'),
            'internship': ('#007bff', '🎓 Stage'),
            'training': ('#6f42c1', '📚 Formation'),
            'apprenticeship': ('#fd7e14', '🔧 Alternance'),
            'volunteer': ('#17a2b8', '❤️ Bénévolat'),
            'project': ('#dc3545', '🚀 Projet'),
        }
        color, text = colors.get(obj.category, ('#6c757d', obj.category))
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, text
        )
    category_badge.short_description = "Catégorie"
    
    def enterprise_name(self, obj):
        """Nom de l'entreprise"""
        if obj.enterprise:
            return obj.enterprise.company_name
        return format_html('<span style="color: gray;">Aucune</span>')
    enterprise_name.short_description = "Entreprise"
    
    def location(self, obj):
        """Localisation"""
        if obj.location_city and obj.location_country:
            return f"{obj.location_city}, {obj.location_country}"
        elif obj.location_city:
            return obj.location_city
        elif obj.location_country:
            return obj.location_country
        return "-"
    location.short_description = "Lieu"
    
    def status_badge(self, obj):
        """Badge de statut"""
        if obj.status == 'open':
            color = 'green' if not obj.is_expired else 'orange'
            text = '🟢 Ouverte' if not obj.is_expired else '⚠️ Ouverte (expirée)'
        else:
            color = 'red'
            text = '🔴 Fermée'
        
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, text)
    status_badge.short_description = "Statut"
    
    def applications_count(self, obj):
        """Nombre de candidatures"""
        count = obj.applications.count()
        if count > 0:
            url = reverse('admin:posts_application_changelist') + f'?opportunity__id__exact={obj.id}'
            return format_html('<a href="{}">{} candidature(s)</a>', url, count)
        return "0"
    applications_count.short_description = "Candidatures"
    
    def applications_stats(self, obj):
        """Statistiques des candidatures"""
        apps = obj.applications.all()
        total = apps.count()
        
        if total == 0:
            return "Aucune candidature"
        
        stats = apps.values('status').annotate(count=Count('status'))
        stats_dict = {item['status']: item['count'] for item in stats}
        
        return format_html(
            '<div style="padding: 15px; background: #f8f9fa; border-radius: 5px;">'
            '<h3>📊 Candidatures</h3>'
            '<p><strong>Total:</strong> {}</p>'
            '<ul>'
            '<li>Soumises: {}</li>'
            '<li>Vues: {}</li>'
            '<li>Présélectionnées: {}</li>'
            '<li>Entretien: {}</li>'
            '<li>Rejetées: {}</li>'
            '<li>Acceptées: {}</li>'
            '</ul>'
            '</div>',
            total,
            stats_dict.get('submitted', 0),
            stats_dict.get('viewed', 0),
            stats_dict.get('shortlisted', 0),
            stats_dict.get('interview', 0),
            stats_dict.get('rejected', 0),
            stats_dict.get('accepted', 0)
        )
    applications_stats.short_description = "Statistiques Candidatures"
    
    def close_opportunities(self, request, queryset):
        """Action pour fermer les opportunités"""
        updated = queryset.update(status='closed')
        self.message_user(request, f"{updated} opportunité(s) fermée(s)")
    close_opportunities.short_description = "🔴 Fermer les opportunités"
    
    def reopen_opportunities(self, request, queryset):
        """Action pour rouvrir les opportunités"""
        updated = queryset.update(status='open')
        self.message_user(request, f"{updated} opportunité(s) rouverte(s)")
    reopen_opportunities.short_description = "🟢 Rouvrir les opportunités"


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Administration des événements"""
    
    list_display = [
        'title', 'starts_at', 'ends_at', 'is_online',
        'location_display', 'capacity_display', 'rsvp_count'
    ]
    list_filter = ['is_online', 'starts_at', 'post__institution']
    search_fields = ['post__title', 'location_name', 'address', 'city']
    readonly_fields = ['rsvp_stats', 'is_full']
    raw_id_fields = ['post']
    
    fieldsets = (
        ('Publication', {
            'fields': ('post',)
        }),
        ('Dates', {
            'fields': ('starts_at', 'ends_at', 'rsvp_deadline')
        }),
        ('Localisation', {
            'fields': ('is_online', 'online_url', 'location_name', 'address', 'city', 'country')
        }),
        ('Capacité', {
            'fields': ('capacity', 'is_full')
        }),
        ('Médias', {
            'fields': ('cover_image',)
        }),
        ('Statistiques', {
            'fields': ('rsvp_stats',),
            'classes': ('collapse',)
        }),
    )
    
    def title(self, obj):
        """Titre"""
        return obj.post.title
    title.short_description = "Titre"
    
    def location_display(self, obj):
        """Affichage de la localisation"""
        if obj.is_online:
            return format_html('<span style="color: blue;">🌐 En ligne</span>')
        elif obj.city:
            return f"📍 {obj.city}"
        return "-"
    location_display.short_description = "Lieu"
    
    def capacity_display(self, obj):
        """Affichage de la capacité"""
        if not obj.capacity:
            return "♾️ Illimitée"
        
        rsvps = obj.rsvps.filter(status=RSVP.Status.GOING).count()
        percentage = (rsvps / obj.capacity * 100)
        color = 'green' if percentage < 70 else 'orange' if percentage < 90 else 'red'
        
        return format_html(
            '<span style="color: {};">{} / {} ({}%)</span>',
            color, rsvps, obj.capacity, round(percentage)
        )
    capacity_display.short_description = "Capacité"
    
    def rsvp_count(self, obj):
        """Nombre de RSVP"""
        count = obj.rsvps.filter(status=RSVP.Status.GOING).count()
        url = reverse('admin:posts_rsvp_changelist') + f'?event__id__exact={obj.id}'
        return format_html('<a href="{}">{} participant(s)</a>', url, count)
    rsvp_count.short_description = "Participants"
    
    def rsvp_stats(self, obj):
        """Statistiques des RSVP"""
        rsvps = obj.rsvps.all()
        total = rsvps.count()
        
        if total == 0:
            return "Aucune réponse"
        
        stats = rsvps.values('status').annotate(count=Count('status'))
        stats_dict = {item['status']: item['count'] for item in stats}
        
        return format_html(
            '<div style="padding: 15px; background: #f8f9fa; border-radius: 5px;">'
            '<h3>📊 Réponses (RSVP)</h3>'
            '<p><strong>Total:</strong> {}</p>'
            '<ul>'
            '<li>✅ Participe: {}</li>'
            '<li>⭐ Intéressé: {}</li>'
            '<li>❌ Ne participe pas: {}</li>'
            '</ul>'
            '</div>',
            total,
            stats_dict.get('going', 0),
            stats_dict.get('interested', 0),
            stats_dict.get('not_going', 0)
        )
    rsvp_stats.short_description = "Statistiques RSVP"


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Administration des projets"""
    
    list_display = [
        'title', 'status_badge', 'team_count', 'looking_for_members',
        'repo_url', 'created_at'
    ]
    list_filter = ['status', 'looking_for_members', 'post__institution']
    search_fields = ['post__title', 'post__content', 'repo_url']
    readonly_fields = ['team_display']
    raw_id_fields = ['post']
    filter_horizontal = ['team']
    
    fieldsets = (
        ('Publication', {
            'fields': ('post',)
        }),
        ('Projet', {
            'fields': ('status', 'looking_for_members', 'required_skills')
        }),
        ('Liens', {
            'fields': ('repo_url', 'demo_url')
        }),
        ('Équipe', {
            'fields': ('team', 'team_display')
        }),
    )
    
    def title(self, obj):
        """Titre"""
        return obj.post.title
    title.short_description = "Titre"
    
    def created_at(self, obj):
        """Date de création"""
        return obj.post.created_at
    created_at.short_description = "Créé le"
    
    def status_badge(self, obj):
        """Badge de statut"""
        colors = {
            'draft': ('gray', '📝 Brouillon'),
            'active': ('green', '🚀 Actif'),
            'completed': ('blue', '✅ Terminé'),
            'archived': ('orange', '📦 Archivé'),
        }
        color, text = colors.get(obj.status, ('gray', obj.status))
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, text)
    status_badge.short_description = "Statut"
    
    def team_count(self, obj):
        """Nombre de membres"""
        return obj.team.count()
    team_count.short_description = "Membres"
    
    def team_display(self, obj):
        """Affichage de l'équipe"""
        members = obj.team.all()
        if not members:
            return "Aucun membre"
        
        html = '<ul>'
        for member in members:
            html += f'<li>{member.get_full_name() or member.username} ({member.role})</li>'
        html += '</ul>'
        
        return format_html(html)
    team_display.short_description = "Équipe"


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """Administration des candidatures"""
    
    list_display = [
        'candidate_name', 'opportunity_title', 'status_badge',
        'created_at', 'updated_at'
    ]
    list_filter = ['status', 'created_at', 'opportunity__category']
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name',
        'opportunity__post__title'
    ]
    readonly_fields = ['created_at', 'updated_at', 'documents_display']
    raw_id_fields = ['user', 'opportunity']
    
    fieldsets = (
        ('Candidature', {
            'fields': ('user', 'opportunity', 'status')
        }),
        ('Documents', {
            'fields': ('resume', 'cover_letter', 'portfolio_url', 'documents_display')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_viewed', 'mark_as_shortlisted', 'mark_as_rejected']
    
    def candidate_name(self, obj):
        """Nom du candidat"""
        return obj.user.get_full_name() or obj.user.username
    candidate_name.short_description = "Candidat"
    
    def opportunity_title(self, obj):
        """Titre de l'opportunité"""
        return obj.opportunity.post.title
    opportunity_title.short_description = "Opportunité"
    
    def status_badge(self, obj):
        """Badge de statut"""
        colors = {
            'submitted': ('#17a2b8', '📤 Soumise'),
            'viewed': ('#ffc107', '👁️ Vue'),
            'shortlisted': ('#28a745', '⭐ Présélectionné'),
            'interview': ('#007bff', '💬 Entretien'),
            'rejected': ('#dc3545', '❌ Rejetée'),
            'accepted': ('#28a745', '✅ Acceptée'),
        }
        color, text = colors.get(obj.status, ('#6c757d', obj.status))
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, text
        )
    status_badge.short_description = "Statut"
    
    def documents_display(self, obj):
        """Affichage des documents"""
        html = '<div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">'
        
        if obj.resume:
            html += f'<p>📄 <strong>CV:</strong> <a href="{obj.resume.url}" target="_blank">Télécharger</a></p>'
        
        if obj.cover_letter:
            html += f'<p>📝 <strong>Lettre:</strong> {len(obj.cover_letter)} caractères</p>'
        
        if obj.portfolio_url:
            html += f'<p>🎨 <strong>Portfolio:</strong> <a href="{obj.portfolio_url}" target="_blank">{obj.portfolio_url}</a></p>'
        
        html += '</div>'
        return format_html(html)
    documents_display.short_description = "Documents"
    
    def mark_as_viewed(self, request, queryset):
        """Marquer comme vue"""
        updated = queryset.update(status='viewed')
        self.message_user(request, f"{updated} candidature(s) marquée(s) comme vue(s)")
    mark_as_viewed.short_description = "👁️ Marquer comme vue"
    
    def mark_as_shortlisted(self, request, queryset):
        """Marquer comme présélectionné"""
        updated = queryset.update(status='shortlisted')
        self.message_user(request, f"{updated} candidature(s) présélectionnée(s)")
    mark_as_shortlisted.short_description = "⭐ Présélectionner"
    
    def mark_as_rejected(self, request, queryset):
        """Marquer comme rejeté"""
        updated = queryset.update(status='rejected')
        self.message_user(request, f"{updated} candidature(s) rejetée(s)")
    mark_as_rejected.short_description = "❌ Rejeter"


# Modèles simples avec admin de base
@admin.register(PostAttachment)
class PostAttachmentAdmin(admin.ModelAdmin):
    list_display = ['post', 'kind', 'file', 'order']
    list_filter = ['kind']
    raw_id_fields = ['post']


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'kind', 'created_at']
    list_filter = ['kind', 'created_at']
    search_fields = ['user__username', 'post__title']
    raw_id_fields = ['user', 'post']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'content_preview', 'created_at']
    list_filter = ['created_at', 'is_edited']
    search_fields = ['user__username', 'post__title', 'content']
    raw_id_fields = ['user', 'post', 'parent']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = "Contenu"


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ['user', 'original', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'original__title']
    raw_id_fields = ['user', 'original']


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'post__title']
    raw_id_fields = ['user', 'post']


@admin.register(RSVP)
class RSVPAdmin(admin.ModelAdmin):
    list_display = ['user', 'event_title', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'event__post__title']
    raw_id_fields = ['user', 'event']
    
    def event_title(self, obj):
        return obj.event.post.title
    event_title.short_description = "Événement"