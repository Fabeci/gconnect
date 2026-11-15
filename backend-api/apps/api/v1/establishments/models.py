"""
G-Connect - Establishments Models (REFONDUS)
Modèles pour la gestion des établissements et promotions avec logique d'ajout automatique
"""

from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import random
import uuid
from django.db import models
from cities_light.models import Country, Region, City


class Institution(models.Model):
    """
    Établissement d'enseignement
    """
    name = models.CharField(max_length=255, verbose_name="Nom de l'établissement")
    slug = models.SlugField(max_length=255, blank=True, null=True, db_index=True)
    acronym = models.CharField(max_length=20, blank=True, verbose_name="Sigle")
    
    text_code = models.CharField(max_length=6, unique=True, blank=True, verbose_name="Code d'enregistrement")
    qr_uuid = models.UUIDField(default=uuid.uuid4, unique=True, blank=True, null=True, verbose_name="QR UUID")

    address = models.TextField(blank=True, verbose_name="Adresse")
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)

    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    email = models.EmailField(blank=True, verbose_name="Email de contact")
    website = models.URLField(blank=True, verbose_name="Site web")

    logo = models.ImageField(upload_to='institutions/logos/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='institutions/covers/', blank=True, null=True)

    established_year = models.PositiveIntegerField(blank=True, null=True, verbose_name="Année de création")
    accreditation = models.CharField(max_length=255, blank=True, verbose_name="Accréditation")
    
    is_active = models.BooleanField(default=True, verbose_name="Établissement actif")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.acronym})" if self.acronym else self.name
    
    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["country", "city"]),
            models.Index(fields=["is_active"]),
        ]

    def save(self, *args, **kwargs):
        if not self.text_code:
            self.text_code = self.generate_unique_code()
        if not self.qr_uuid:
            import uuid as _uuid
            self.qr_uuid = _uuid.uuid4()

        if not self.slug:
            from django.utils.text import slugify
            base = slugify(f"{self.name}-{self.acronym or ''}") or slugify(self.name) or "institution"
            candidate = base
            i = 1
            while Institution.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                i += 1
                candidate = f"{base}-{i}"
            self.slug = candidate
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Créer automatiquement la promotion générale si c'est un nouvel établissement
        if is_new:
            self.create_general_promotion()

    def generate_unique_code(self):
        while True:
            code = f"{random.randint(100000, 999999)}"
            if not Institution.objects.filter(text_code=code).exists():
                return code

    def regenerate_codes(self):
        self.text_code = self.generate_unique_code()
        self.qr_uuid = uuid.uuid4()
        self.save()
    
    def create_general_promotion(self):
        """Crée la promotion générale si elle n'existe pas déjà.

        La propriété general_promotion existe toujours sur le modèle :
        hasattr(self, 'general_promotion') ne vérifie donc pas la présence
        d'une promotion en base. La contrainte unique protège également
        contre la création de plusieurs promotions générales.
        """
        promotion, _ = Promotion.objects.get_or_create(
            institution=self,
            is_general=True,
            defaults={
                "name": f"Promotion Générale - {self.name}"[:100],
                "description": f"Promotion générale de tous les membres de {self.name}",
            },
        )
        return promotion
    
    @property
    def general_promotion(self):
        """Retourne la promotion générale de l'établissement"""
        return self.promotions.filter(is_general=True).first()


class StudentInstitution(models.Model):
    """
    Relation entre un étudiant et un établissement
    À la création, l'étudiant est automatiquement ajouté à la promotion générale
    """
    student = models.ForeignKey('users.Student', on_delete=models.CASCADE)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_primary = models.BooleanField(default=False)  # Premier établissement
    is_active = models.BooleanField(default=True, verbose_name="Inclus dans le fil d'actualité")
    # Distinct from is_active, which only controls the news feed.
    seat_enabled = models.BooleanField(default=True, verbose_name="Compte autorisé par l'établissement")

    class Meta:
        unique_together = ('student', 'institution')
        indexes = [
            models.Index(fields=['student', 'institution']),
            models.Index(fields=['student', 'is_active']),
        ]

    def __str__(self):
        return f"{self.student.user.username} @ {self.institution.name}"


class AlumniInstitution(models.Model):
    """
    Relation entre un alumni et un établissement
    À la création, l'alumni est automatiquement ajouté à la promotion générale
    """
    alumni = models.ForeignKey('users.Alumni', on_delete=models.CASCADE)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name="Inclus dans le fil d'actualité")
    seat_enabled = models.BooleanField(default=True, verbose_name="Compte autorisé par l'établissement")

    class Meta:
        unique_together = ('alumni', 'institution')
        indexes = [
            models.Index(fields=['alumni', 'institution']),
            models.Index(fields=['alumni', 'is_active']),
        ]

    def __str__(self):
        return f"{self.alumni.user.username} @ {self.institution.name}"


class Promotion(models.Model):
    """
    Promotion au sein d'un établissement
    - Une promotion générale par établissement (créée automatiquement)
    - Promotions spécifiques (par filière, classe, année, etc.)
    - Chaque promotion a automatiquement un groupe de discussion associé
    """
    name = models.CharField(max_length=100)  # ex : Générale, L2 Info, M1 Droit, Promo 2024
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='promotions')
    is_general = models.BooleanField(default=False, verbose_name="Promotion générale")
    description = models.TextField(null=True, blank=True)
    
    # Informations supplémentaires pour promotions spécifiques
    year = models.PositiveIntegerField(null=True, blank=True, verbose_name="Année")
    department = models.CharField(max_length=100, blank=True, verbose_name="Département/Filière")
    level = models.CharField(
        max_length=50, 
        blank=True,
        choices=[
            ('L1', 'Licence 1'),
            ('L2', 'Licence 2'),
            ('L3', 'Licence 3'),
            ('M1', 'Master 1'),
            ('M2', 'Master 2'),
            ('D', 'Doctorat'),
            ('OTHER', 'Autre'),
        ]
    )
    
    # Image de la promotion
    cover_image = models.ImageField(upload_to='promotions/covers/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.institution.name}"
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['institution'],
                condition=models.Q(is_general=True),
                name='unique_general_promotion_per_institution'
            )
        ]
        indexes = [
            models.Index(fields=['institution', 'name']),
            models.Index(fields=['is_general']),
        ]
    
    @property
    def members_count(self):
        """Compte le nombre total de membres"""
        return self.members.filter(is_approved=True).count()
    
    @property
    def pending_requests_count(self):
        """Compte les demandes en attente"""
        return self.join_requests.filter(status='pending').count()


class PromotionMembership(models.Model):
    """
    Appartenance d'un étudiant à une promotion
    - Automatiquement approuvée pour la promotion générale
    - Nécessite approbation pour les promotions spécifiques
    """
    student = models.ForeignKey('users.Student', on_delete=models.CASCADE, related_name='promotion_memberships')
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='members')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)  # Si une demande est en attente
    is_delegate = models.BooleanField(default=False, verbose_name="Délégué de promotion")
    is_active = models.BooleanField(default=True, verbose_name="Incluse dans le fil d'actualité")

    # Approbation
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_memberships'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'promotion')
        indexes = [
            models.Index(fields=['promotion', 'is_approved']),
            models.Index(fields=['student', 'is_approved']),
            models.Index(fields=['student', 'is_active']),
        ]

    def __str__(self):
        status = "✓" if self.is_approved else "⏳"
        delegate = " [Délégué]" if self.is_delegate else ""
        return f"{status} {self.student.user.username} → {self.promotion.name}{delegate}"
    
    def approve(self, approved_by_user):
        """Approuve l'adhésion à la promotion"""
        self.is_approved = True
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        self.save()


class AlumniPromotionMembership(models.Model):
    """
    Appartenance d'un alumni à une promotion
    Même logique que pour les étudiants
    """
    alumni = models.ForeignKey('users.Alumni', on_delete=models.CASCADE, related_name='promotion_memberships')
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='alumni_members')
    joined_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, verbose_name="Incluse dans le fil d'actualité")

    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_alumni_memberships'
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('alumni', 'promotion')
        indexes = [
            models.Index(fields=['promotion', 'is_approved']),
            models.Index(fields=['alumni', 'is_active']),
        ]

    def __str__(self):
        status = "✓" if self.is_approved else "⏳"
        return f"{status} {self.alumni.user.username} → {self.promotion.name}"
    
    def approve(self, approved_by_user):
        """Approuve l'adhésion à la promotion"""
        self.is_approved = True
        self.approved_by = approved_by_user
        self.approved_at = timezone.now()
        self.save()


class PromotionJoinRequest(models.Model):
    """
    Demande d'adhésion à une promotion spécifique
    Peut être validée par :
    - Un délégué de la promotion (is_delegate=True)
    - L'admin de l'établissement
    """
    student = models.ForeignKey('users.Student', on_delete=models.CASCADE, related_name='join_requests', null=True, blank=True)
    alumni = models.ForeignKey('users.Alumni', on_delete=models.CASCADE, related_name='join_requests', null=True, blank=True)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='join_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    motivation = models.TextField(blank=True, verbose_name="Motivation de la demande")
    status = models.CharField(
        max_length=20, 
        choices=[
            ('pending', 'En attente'),
            ('accepted', 'Acceptée'),
            ('rejected', 'Rejetée')
        ], 
        default='pending'
    )
    
    # Traitement de la demande
    processed_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_join_requests',
        verbose_name="Traitée par"
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        unique_together = [
            ('student', 'promotion'),
            ('alumni', 'promotion'),
        ]
        indexes = [
            models.Index(fields=['promotion', 'status']),
            models.Index(fields=['student', 'status']),
            models.Index(fields=['alumni', 'status']),
        ]

    def __str__(self):
        user = self.student.user if self.student else self.alumni.user
        return f"Demande de {user.username} pour {self.promotion.name} [{self.status}]"
    
    def can_be_approved_by(self, user):
        """
        Vérifie si un utilisateur peut approuver cette demande
        - Admin de l'établissement
        - Délégué de la promotion
        """
        # Admin de l'établissement
        if hasattr(user, 'institution_admin_profile'):
            if user.institution_admin_profile.institution == self.promotion.institution:
                return True
        
        # Délégué de la promotion
        if self.student:
            delegate = self.promotion.members.filter(
                student__user=user,
                is_delegate=True,
                is_approved=True
            ).exists()
            if delegate:
                return True
        
        return False
    
    def accept(self, processed_by_user):
        """Accepte la demande et crée l'adhésion"""
        if not self.can_be_approved_by(processed_by_user):
            raise PermissionError("Vous n'avez pas la permission d'approuver cette demande")
        
        self.status = 'accepted'
        self.processed_by = processed_by_user
        self.processed_at = timezone.now()
        self.save()
        
        # Créer l'adhésion
        if self.student:
            membership, created = PromotionMembership.objects.get_or_create(
                student=self.student,
                promotion=self.promotion
            )
            membership.approve(processed_by_user)
        elif self.alumni:
            membership, created = AlumniPromotionMembership.objects.get_or_create(
                alumni=self.alumni,
                promotion=self.promotion
            )
            membership.approve(processed_by_user)
    
    def reject(self, processed_by_user, reason=""):
        """Rejette la demande"""
        if not self.can_be_approved_by(processed_by_user):
            raise PermissionError("Vous n'avez pas la permission de rejeter cette demande")
        
        self.status = 'rejected'
        self.processed_by = processed_by_user
        self.processed_at = timezone.now()
        self.rejection_reason = reason
        self.save()


class PromotionDiscussionGroup(models.Model):
    """
    Groupe de discussion associé à une promotion
    Créé automatiquement à la création de la promotion
    Le créateur est l'admin de l'établissement
    """
    promotion = models.OneToOneField(
        Promotion, 
        on_delete=models.CASCADE, 
        related_name='discussion_group'
    )
    conversation = models.OneToOneField(
        'messaging.Conversation',  # Référence au modèle Conversation de messaging
        on_delete=models.CASCADE,
        related_name='promotion_group'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Groupe de discussion: {self.promotion.name}"
    
    class Meta:
        verbose_name = "Groupe de discussion de promotion"
        verbose_name_plural = "Groupes de discussion de promotions"


class StudentAccountOrder(models.Model):
    """
    Commande de comptes étudiants par un établissement
    """
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('approved', 'Approuvée'),
        ('rejected', 'Rejetée'),
    ]

    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='account_orders')
    year = models.PositiveIntegerField(default=timezone.now().year)
    quantity = models.PositiveIntegerField()
    price_per_account = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    used_accounts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_price(self):
        if self.quantity is None or self.price_per_account is None:
            return 0
        return self.quantity * self.price_per_account
    
    @property
    def total_price_display(self):
        return f"{self.total_price:.2f} €"

    @property
    def remaining(self):
        if self.quantity is None or self.used_accounts is None:
            return 0
        return self.quantity - self.used_accounts

    def increment_usage(self):
        if self.status != 'approved':
            raise ValueError("Commande non validée.")
        if self.remaining <= 0:
            raise ValueError("Plus de comptes disponibles.")
        self.used_accounts += 1
        self.save()

    def __str__(self):
        return f"Commande {self.id} ({self.institution.name}) - {self.status}"


# ==================== SIGNALS ====================

@receiver(post_save, sender=StudentInstitution)
def add_student_to_general_promotion(sender, instance, created, raw=False, **kwargs):
    """
    Signal: Ajoute automatiquement un étudiant à la promotion générale
    lorsqu'il rejoint un établissement
    """
    if raw:
        return

    if created:
        general_promo = instance.institution.general_promotion
        if general_promo:
            membership, _ = PromotionMembership.objects.get_or_create(
                student=instance.student,
                promotion=general_promo,
                defaults={'is_approved': True}  # Auto-approuvé pour promotion générale
            )
            # Si déjà existant, s'assurer qu'il est approuvé
            if not membership.is_approved:
                membership.is_approved = True
                membership.save()


@receiver(post_save, sender=AlumniInstitution)
def add_alumni_to_general_promotion(sender, instance, created, raw=False, **kwargs):
    """
    Signal: Ajoute automatiquement un alumni à la promotion générale
    lorsqu'il rejoint un établissement
    """
    if raw:
        return

    if created:
        general_promo = instance.institution.general_promotion
        if general_promo:
            membership, _ = AlumniPromotionMembership.objects.get_or_create(
                alumni=instance.alumni,
                promotion=general_promo,
                defaults={'is_approved': True}  # Auto-approuvé pour promotion générale
            )
            if not membership.is_approved:
                membership.is_approved = True
                membership.save()


@receiver(post_save, sender=Promotion)
def create_promotion_discussion_group(sender, instance, created, raw=False, **kwargs):
    """
    Signal: Crée automatiquement un groupe de discussion
    lorsqu'une promotion est créée
    """
    if raw:
        return

    if created:
        from apps.api.v1.messaging.models import Conversation, ConversationParticipant
        
        # Récupérer l'admin de l'établissement
        admin_user = None
        if hasattr(instance.institution, 'institution_admin_profile'):
            admin_user = instance.institution.institution_admin_profile.user
        
        # Créer la conversation de groupe
        conversation = Conversation.objects.create(
            conversation_type=Conversation.ConversationType.GROUP,
            name=f"💬 {instance.name}",
            description=f"Groupe de discussion de la promotion {instance.name}",
            created_by=admin_user
        )
        
        # Ajouter l'admin comme participant
        if admin_user:
            ConversationParticipant.objects.create(
                conversation=conversation,
                user=admin_user,
                role=ConversationParticipant.Role.ADMIN
            )
        
        # Créer le lien promotion-groupe
        PromotionDiscussionGroup.objects.create(
            promotion=instance,
            conversation=conversation
        )
