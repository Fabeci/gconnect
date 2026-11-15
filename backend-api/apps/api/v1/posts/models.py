"""
G-Connect - Posts Models (REFONDUS)
Modèles pour les publications avec logique d'opportunités et audience
"""

import mimetypes
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator

from apps.api.v1.establishments.models import Institution, Promotion
from apps.api.v1.users.models import Enterprise


# ─── Validators ──────────────────────────────────────────────────────────────

_ALLOWED_MEDIA_MIMES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp',
    'video/mp4', 'video/webm', 'video/quicktime',
    'application/pdf',
}
_MAX_MEDIA_BYTES = 50 * 1024 * 1024  # 50 Mo


def validate_post_media(value):
    if hasattr(value, 'size') and value.size > _MAX_MEDIA_BYTES:
        mb = value.size / (1024 * 1024)
        raise ValidationError(
            f"Le fichier dépasse la taille maximale autorisée (50 Mo). "
            f"Taille actuelle : {mb:.1f} Mo."
        )
    mime, _ = mimetypes.guess_type(value.name)
    if mime not in _ALLOWED_MEDIA_MIMES:
        raise ValidationError(
            f"Type de fichier non autorisé ({mime or 'inconnu'}). "
            "Types acceptés : JPG, PNG, GIF, WEBP, MP4, WEBM, MOV, PDF."
        )

User = get_user_model()


class Post(models.Model):
    """
    Publication générale sur G-Connect
    Peut être :
    - Une opportunité (stage, emploi, formation, etc.)
    - Un événement
    - Un projet
    - Une discussion simple
    - Un partage
    
    L'audience détermine qui peut voir le post :
    - Public : tout le monde
    - Promotion générale : tous les membres de l'établissement
    - Promotion spécifique : membres d'une promotion choisie
    """
    
    class PostType(models.TextChoices):
        OPPORTUNITY = "opportunity", "Opportunité"
        EVENT = "event", "Événement"
        PROJECT = "project", "Projet"
        DISCUSSION = "discussion", "Discussion"
        SHARE = "share", "Partage"

    class Audience(models.TextChoices):
        PUBLIC = "public", "Public (tout le monde)"
        GENERAL_PROMOTION = "general_promotion", "Promotion générale"
        SPECIFIC_PROMOTION = "specific_promotion", "Promotion(s) spécifique(s)"

    # Auteur (Étudiant, Alumni, Admin Établissement, ou Entreprise)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posts")
    
    # Établissement lié (si l'auteur est étudiant/alumni/admin établissement)
    institution = models.ForeignKey(
        Institution, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="posts"
    )
    
    # Contenu
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True, validators=[MaxLengthValidator(5000)])
    
    # Type et audience
    post_type = models.CharField(
        max_length=20, 
        choices=PostType.choices, 
        default=PostType.DISCUSSION
    )
    audience = models.CharField(
        max_length=30,
        choices=Audience.choices, 
        default=Audience.PUBLIC
    )
    
    # Promotions cibles (pour audience SPECIFIC_PROMOTION)
    promotion_targets = models.ManyToManyField(
        Promotion, 
        blank=True, 
        related_name="targeted_posts",
        verbose_name="Promotions cibles"
    )
    
    # Statistiques d'engagement
    reactions_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    
    # Gestion
    is_pinned = models.BooleanField(default=False, verbose_name="Épinglé")
    is_archived = models.BooleanField(default=False, verbose_name="Archivé")
    is_draft = models.BooleanField(default=False, verbose_name="Brouillon", db_index=True)
    is_hidden_by_admin = models.BooleanField(default=False, verbose_name="Masqué par modération", db_index=True)
    hidden_reason = models.CharField(max_length=255, blank=True, default='')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at", "post_type"]),
            models.Index(fields=["audience"]),
            models.Index(fields=["author", "-created_at"]),
            models.Index(fields=["institution", "-created_at"]),
        ]
        verbose_name = "Publication"
        verbose_name_plural = "Publications"

    def __str__(self):
        return f"{self.get_post_type_display()}: {self.title}"
    
    def clean(self):
        """Validation des règles métier"""
        super().clean()
        
        # Si audience = SPECIFIC_PROMOTION, au moins une promotion doit être sélectionnée
        if self.audience == self.Audience.SPECIFIC_PROMOTION:
            if self.pk:  # Seulement après création
                if not self.promotion_targets.exists():
                    raise ValidationError({
                        'promotion_targets': 'Vous devez sélectionner au moins une promotion pour cette audience.'
                    })
        
        # Si audience = GENERAL_PROMOTION, l'institution doit être définie
        if self.audience == self.Audience.GENERAL_PROMOTION:
            if not self.institution:
                raise ValidationError({
                    'institution': 'L\'établissement est requis pour cibler la promotion générale.'
                })
    
    def can_user_view(self, user):
        """
        Vérifie si un utilisateur peut voir ce post selon l'audience
        """
        # Public : tout le monde peut voir
        if self.audience == self.Audience.PUBLIC:
            return True
        
        # Promotion générale : membres de l'établissement
        if self.audience == self.Audience.GENERAL_PROMOTION:
            if self.institution:
                # Vérifier si l'utilisateur est membre de l'établissement
                if hasattr(user, 'student_profile'):
                    return user.student_profile.institutions.filter(id=self.institution.id).exists()
                elif hasattr(user, 'alumni_profile'):
                    return user.alumni_profile.institution == self.institution
                elif hasattr(user, 'institution_admin_profile'):
                    return user.institution_admin_profile.institution == self.institution
        
        # Promotion spécifique : membres des promotions cibles
        if self.audience == self.Audience.SPECIFIC_PROMOTION:
            if hasattr(user, 'student_profile'):
                # Vérifier si l'étudiant est dans une des promotions cibles
                user_promotions = user.student_profile.promotion_memberships.filter(
                    is_approved=True
                ).values_list('promotion_id', flat=True)
                return self.promotion_targets.filter(id__in=user_promotions).exists()
            elif hasattr(user, 'alumni_profile'):
                # Vérifier si l'alumni est dans une des promotions cibles
                user_promotions = user.alumni_profile.promotion_memberships.filter(
                    is_approved=True
                ).values_list('promotion_id', flat=True)
                return self.promotion_targets.filter(id__in=user_promotions).exists()
        
        return False


class PostAttachment(models.Model):
    """
    Pièces jointes d'un post
    """
    class Kind(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Vidéo"
        FILE = "file", "Fichier"

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="post_media/", validators=[validate_post_media])
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.IMAGE)
    alt_text = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.get_kind_display()} pour {self.post.title}"


class Opportunity(models.Model):
    """
    Opportunité professionnelle
    Peut être :
    - Un stage
    - Un emploi
    - Une formation
    - Etc.
    
    La catégorie détermine les champs requis et l'affichage
    """
    
    class WorkMode(models.TextChoices):
        ONSITE = "onsite", "Sur site"
        REMOTE = "remote", "À distance"
        HYBRID = "hybrid", "Hybride"

    class ContractType(models.TextChoices):
        PERMANENT = "permanent", "CDI"
        FIXED_TERM = "fixed_term", "CDD"
        INTERNSHIP = "internship", "Stage"
        APPRENTICESHIP = "apprenticeship", "Alternance"
        FREELANCE = "freelance", "Freelance"
        VOLUNTEER = "volunteer", "Bénévolat"

    class Status(models.TextChoices):
        OPEN = "open", "Ouverte"
        CLOSED = "closed", "Fermée"

    class Category(models.TextChoices):
        JOB = "job", "Emploi"
        INTERNSHIP = "internship", "Stage"
        TRAINING = "training", "Formation"
        APPRENTICESHIP = "apprenticeship", "Alternance"
        VOLUNTEER = "volunteer", "Bénévolat"
        PROJECT = "project", "Projet collaboratif"

    post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name="opportunity")
    
    # Entreprise (optionnel car peut être publié par un étudiant/alumni/admin)
    enterprise = models.ForeignKey(
        Enterprise, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="opportunities"
    )
    
    # Catégorie de l'opportunité (détermine les champs à remplir)
    category = models.CharField(
        max_length=20, 
        choices=Category.choices, 
        default=Category.JOB
    )
    
    # Localisation
    location_city = models.CharField(max_length=120, blank=True)
    location_country = models.CharField(max_length=120, blank=True)
    work_mode = models.CharField(
        max_length=10, 
        choices=WorkMode.choices, 
        default=WorkMode.ONSITE
    )
    
    # Type de contrat (si applicable selon catégorie)
    contract_type = models.CharField(
        max_length=20, 
        choices=ContractType.choices, 
        blank=True
    )
    
    # Statut
    status = models.CharField(
        max_length=10, 
        choices=Status.choices, 
        default=Status.OPEN
    )
    
    # Candidature
    application_url = models.URLField(blank=True, verbose_name="URL de candidature")
    application_email = models.EmailField(blank=True, verbose_name="Email de candidature")
    deadline = models.DateField(blank=True, null=True, verbose_name="Date limite")
    
    # Rémunération (optionnel selon catégorie)
    salary_min = models.PositiveIntegerField(blank=True, null=True)
    salary_max = models.PositiveIntegerField(blank=True, null=True)
    currency = models.CharField(max_length=10, default="XOF", blank=True)
    
    # Durée (pour stages, formations, etc.)
    duration_months = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Durée en mois"
    )

    # Tags et compétences
    tags = models.JSONField(blank=True, null=True, default=list)
    required_skills = models.JSONField(blank=True, null=True, default=list)

    # Informations spécifiques selon catégorie
    start_date = models.DateField(blank=True, null=True, verbose_name="Date de début")

    # Spécifique aux formations (category=TRAINING)
    instructor = models.CharField(max_length=255, blank=True, verbose_name="Intervenant")
    # IntegerField (plutôt que PositiveIntegerField) : évite la contrainte CHECK
    # que Django ajoute pour les entiers positifs sur SQLite, qui forcerait une
    # reconstruction de table lors de l'ALTER TABLE (ADD COLUMN simple sinon).
    available_spots = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Places disponibles"
    )
    
    class Meta:
        verbose_name = "Opportunité"
        verbose_name_plural = "Opportunités"
        ordering = ["-post__created_at"]
        indexes = [
            models.Index(fields=["category", "status"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.get_category_display()}: {self.post.title}"
    
    def clean(self):
        """Validation selon la catégorie"""
        super().clean()
        
        # Pour les stages et alternances, la durée est requise
        if self.category in [self.Category.INTERNSHIP, self.Category.APPRENTICESHIP]:
            if not self.duration_months:
                raise ValidationError({
                    'duration_months': f'La durée est requise pour un(e) {self.get_category_display()}'
                })
        
        # Pour les emplois, le type de contrat est requis
        if self.category == self.Category.JOB:
            if not self.contract_type:
                raise ValidationError({
                    'contract_type': 'Le type de contrat est requis pour un emploi'
                })
    
    @property
    def is_expired(self):
        """Vérifie si l'opportunité a expiré"""
        if not self.deadline:
            return False
        from django.utils import timezone
        return timezone.now().date() > self.deadline


class Event(models.Model):
    """
    Événement
    """
    post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name="event")
    starts_at = models.DateTimeField(verbose_name="Date et heure de début")
    ends_at = models.DateTimeField(blank=True, null=True, verbose_name="Date et heure de fin")
    is_online = models.BooleanField(default=False, verbose_name="Événement en ligne")
    
    # Localisation physique
    location_name = models.CharField(max_length=255, blank=True, verbose_name="Nom du lieu")
    address = models.CharField(max_length=255, blank=True, verbose_name="Adresse")
    city = models.CharField(max_length=120, blank=True, verbose_name="Ville")
    country = models.CharField(max_length=120, blank=True, verbose_name="Pays")
    
    # URL pour événements en ligne
    online_url = models.URLField(blank=True, verbose_name="Lien de l'événement")
    
    # Image de couverture
    cover_image = models.ImageField(upload_to="events/", blank=True, null=True)
    
    # Capacité
    capacity = models.PositiveIntegerField(
        blank=True, 
        null=True,
        verbose_name="Capacité maximale"
    )
    rsvp_deadline = models.DateTimeField(
        blank=True, 
        null=True,
        verbose_name="Date limite d'inscription"
    )

    class Meta:
        verbose_name = "Événement"
        verbose_name_plural = "Événements"
        ordering = ["starts_at"]

    def __str__(self):
        return f"Événement: {self.post.title}"
    
    @property
    def is_full(self):
        """Vérifie si l'événement est complet"""
        if not self.capacity:
            return False
        return self.rsvps.filter(status=RSVP.Status.GOING).count() >= self.capacity


class Project(models.Model):
    """
    Projet collaboratif
    """
    class Status(models.TextChoices):
        DRAFT = "draft", "Brouillon"
        ACTIVE = "active", "Actif"
        COMPLETED = "completed", "Terminé"
        ARCHIVED = "archived", "Archivé"

    post = models.OneToOneField(Post, on_delete=models.CASCADE, related_name="project")
    status = models.CharField(
        max_length=10, 
        choices=Status.choices, 
        default=Status.ACTIVE
    )
    
    # Liens
    repo_url = models.URLField(blank=True, verbose_name="Lien du dépôt (GitHub, etc.)")
    demo_url = models.URLField(blank=True, verbose_name="Lien de la démo")
    
    # Équipe
    team = models.ManyToManyField(
        User, 
        blank=True, 
        related_name="project_team",
        verbose_name="Membres de l'équipe"
    )
    
    # Recherche de membres
    looking_for_members = models.BooleanField(
        default=True,
        verbose_name="Recherche de membres"
    )
    required_skills = models.JSONField(
        blank=True, 
        null=True, 
        default=list,
        verbose_name="Compétences recherchées"
    )

    class Meta:
        verbose_name = "Projet"
        verbose_name_plural = "Projets"

    def __str__(self):
        return f"Projet: {self.post.title}"


class Reaction(models.Model):
    """
    Réaction à un post
    """
    class Kind(models.TextChoices):
        LIKE = "like", "J'aime"
        CELEBRATE = "celebrate", "Bravo"
        SUPPORT = "support", "Soutien"
        LOVE = "love", "Adore"
        INSIGHTFUL = "insightful", "Instructif"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reactions")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reactions")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.LIKE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")
        indexes = [
            models.Index(fields=["post", "kind"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.get_kind_display()}"


class Comment(models.Model):
    """
    Commentaire sur un post
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="comments")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    parent = models.ForeignKey(
        "self", 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name="replies"
    )
    content = models.TextField(validators=[MaxLengthValidator(2000)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["post", "created_at"]),
        ]

    def __str__(self):
        return f"Commentaire de {self.user.username}"


class CommentLike(models.Model):
    """Like sur un commentaire."""
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('comment', 'user')
        indexes = [models.Index(fields=['comment'])]

    def __str__(self):
        return f"{self.user.username} aime le commentaire #{self.comment_id}"


class Share(models.Model):
    """
    Partage d'un post
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="shares")
    original = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="shared_instances")
    comment = models.TextField(blank=True, verbose_name="Commentaire du partage")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["original", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} a partagé {self.original.title}"


class Bookmark(models.Model):
    """
    Sauvegarde d'un post
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookmarks")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="bookmarked_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.user.username} a sauvegardé {self.post.title}"


class Application(models.Model):
    """
    Candidature à une opportunité
    """
    STATUS = [
        ("submitted", "Soumise"),
        ("viewed", "Vue"),
        ("shortlisted", "Présélectionné"),
        ("interview", "Entretien"),
        ("rejected", "Rejetée"),
        ("accepted", "Acceptée"),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="applications")
    opportunity = models.ForeignKey(Opportunity, on_delete=models.CASCADE, related_name="applications")
    
    # Documents
    resume = models.FileField(upload_to="applications/resumes/", blank=True, null=True)
    cover_letter = models.TextField(blank=True, verbose_name="Lettre de motivation")
    portfolio_url = models.URLField(blank=True, verbose_name="Lien du portfolio")
    
    # Statut
    status = models.CharField(max_length=20, choices=STATUS, default="submitted")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "opportunity")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["opportunity", "status"]),
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"Candidature de {self.user.username} pour {self.opportunity.post.title}"


class RSVP(models.Model):
    """
    Réponse à un événement
    """
    class Status(models.TextChoices):
        GOING = "going", "Participe"
        INTERESTED = "interested", "Intéressé"
        NOT_GOING = "not_going", "Ne participe pas"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="rsvps")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="rsvps")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.GOING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "event")
        verbose_name = "RSVP"
        verbose_name_plural = "RSVPs"

    def __str__(self):
        return f"{self.user.username} - {self.get_status_display()}"