# models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.api.v1.core.models import Interest, Preference, Sector, Skill
from apps.api.v1.establishments.models import Institution, Promotion

class User(AbstractUser):
    ROLES = (
        ('student', 'Étudiant'),
        ('alumni', 'Alumni'),
        ('enterprise', 'Entreprise'),
        ('etablissement', 'Admin Établissement'),
        ('superAdmin', 'Super Admin'),
    )
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLES, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True, db_column='phone_number')
    photo = models.ImageField(upload_to='avatars/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='avatars/covers/', blank=True, null=True)
    bio = models.TextField(blank=True, default='')
    location = models.CharField(max_length=150, blank=True, default='')
    is_active = models.BooleanField(default=False, db_index=True)
    is_banned = models.BooleanField(default=False, verbose_name="Banni", db_index=True)
    banned_reason = models.CharField(max_length=255, blank=True, default='')
    banned_at = models.DateTimeField(null=True, blank=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.username} ({self.role})"
    

class Student(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    student_id = models.CharField(max_length=110, unique=True, null=True)
    interests = models.ManyToManyField(Interest, related_name='students_interested', blank=True)
    preferences = models.ManyToManyField(Preference, related_name='students_with_preferences', blank=True)
    sectors = models.ManyToManyField(Sector, related_name='students_in_sectors', blank=True)
    skills = models.ManyToManyField(Skill, related_name='students_with_skills', blank=True)

    # Relation avec plusieurs établissements
    institutions = models.ManyToManyField(Institution, through='establishments.StudentInstitution', related_name='students')

    def __str__(self):
        return self.user.get_full_name()


class Alumni(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='alumni_profile')
    gender = models.CharField(max_length=10)
    proof_document = models.FileField(upload_to="alumni_proofs/")
    graduation_date = models.DateField(null=True, blank=True)
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)
    promotion = models.ForeignKey(Promotion, on_delete=models.SET_NULL, null=True, blank=True)

    interests = models.ManyToManyField(Interest, related_name='alumni_interested', blank=True)
    preferences = models.ManyToManyField(Preference, related_name='alumni_with_preferences', blank=True)
    sectors = models.ManyToManyField(Sector, related_name='alumni_in_sectors', blank=True)
    skills = models.ManyToManyField(Skill, related_name='alumni_with_skills', blank=True)

    def __str__(self):
        return self.user.get_full_name()


class InstitutionAdmin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='institution_admin_profile')
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE)

    def __str__(self):
        return f"Admin {self.user.username}"


class Enterprise(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='enterprise_profile')
    company_name = models.CharField(max_length=255)
    sector = models.CharField(max_length=100)
    website = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.company_name


class EnterpriseMember(models.Model):
    """A recruiter belongs to exactly one verified company account."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="enterprise_membership")
    enterprise = models.ForeignKey(Enterprise, on_delete=models.CASCADE, related_name="recruiters")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=["enterprise", "is_active"], name="users_e53_member_status_idx")]


class EnterpriseInvitation(models.Model):
    """Hashed, short-lived invitation; the emailed link proves address ownership."""
    KIND_OWNER = "owner"
    KIND_RECRUITER = "recruiter"
    KINDS = [(KIND_OWNER, "Responsable"), (KIND_RECRUITER, "Recruteur")]

    email = models.EmailField(db_index=True)
    kind = models.CharField(max_length=12, choices=KINDS)
    company_name = models.CharField(max_length=255, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    enterprise = models.ForeignKey(
        Enterprise, null=True, blank=True, on_delete=models.PROTECT, related_name="invitations",
    )
    invited_by = models.ForeignKey(
        User, null=True, on_delete=models.SET_NULL, related_name="sent_enterprise_invitations",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    accepted_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="accepted_enterprise_invitations",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email", "-created_at"], name="users_e53_inv_email_idx")]


class ProfilePrivacy(models.Model):
    """
    Visibilité par champ du profil — 5 niveaux, du plus ouvert au plus
    fermé. `profile_visibility` conditionne l'accès à la fiche entière (si
    non visible, les autres champs ne sont même pas évalués) ; les autres
    champs affinent ensuite ce qui est montré à l'intérieur d'une fiche
    accessible.
    """

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        MEMBERS = "members", "Membres uniquement"
        SAME_INSTITUTION = "same_institution", "Même établissement"
        CONNECTIONS = "connections", "Mes relations"
        PRIVATE = "private", "Privé"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='privacy_settings')
    profile_visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)
    photo_visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)
    cover_visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)
    phone_visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.CONNECTIONS)
    email_visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.CONNECTIONS)
    experience_visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.MEMBERS)
    cv_visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.CONNECTIONS)
    skills_visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)
    posts_visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)

    def __str__(self):
        return f"Confidentialité de {self.user.username}"

    @classmethod
    def for_user(cls, user):
        obj, _ = cls.objects.get_or_create(user=user)
        return obj

    def can_view(self, viewer, field):
        """`field` est l'un des `xxx_visibility` ci-dessus (sans le suffixe),
        ex. `can_view(viewer, 'photo')`."""
        if viewer is not None and viewer.is_authenticated and viewer.id == self.user_id:
            return True

        level = getattr(self, f"{field}_visibility")
        if level == self.Visibility.PUBLIC:
            return True
        if level == self.Visibility.PRIVATE:
            return False
        if viewer is None or not viewer.is_authenticated:
            return False
        if level == self.Visibility.MEMBERS:
            return True
        if level == self.Visibility.SAME_INSTITUTION:
            return _shares_institution(viewer, self.user)
        if level == self.Visibility.CONNECTIONS:
            from apps.api.v1.networking.models import Connection
            return Connection.are_connected(viewer, self.user)
        return False


def _shares_institution(user_a, user_b):
    """Institutions de chacun (étudiant : plusieurs via M2M ; alumni/admin :
    une seule via FK) — vrai si elles se recoupent."""
    def institution_ids(user):
        if hasattr(user, "student_profile"):
            return set(user.student_profile.institutions.values_list("id", flat=True))
        if hasattr(user, "alumni_profile") and user.alumni_profile.institution_id:
            return {user.alumni_profile.institution_id}
        if hasattr(user, "institution_admin_profile"):
            return {user.institution_admin_profile.institution_id}
        return set()

    return bool(institution_ids(user_a) & institution_ids(user_b))


class LoginAttempt(models.Model):
    """
    Historique des tentatives de connexion (réussies ou non), utilisé pour
    limiter le rythme des tentatives (`LoginView`) — voir la fenêtre glissante
    dans `views.py`. Conservé aussi pour les échecs (traçabilité).
    """
    email = models.CharField(max_length=255, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    success = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        indexes = [models.Index(fields=["email", "success", "created_at"])]

    def __str__(self):
        return f"{self.email} - {'OK' if self.success else 'échec'} - {self.created_at}"


class LoginSession(models.Model):
    """
    Historique des connexions réussies — alimente l'écran 'Appareils
    connectés' / 'Historique des connexions' des Paramètres. Note : DRF
    `authtoken` n'attribue qu'un seul jeton par utilisateur (partagé entre
    appareils) ; une vraie révocation par appareil demanderait de migrer
    vers un jeton par session, hors périmètre de ce chantier. La révocation
    disponible ici (`révoquer toutes les sessions`) invalide donc le jeton
    partagé, ce qui déconnecte tous les appareils à la fois.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_sessions")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"Connexion de {self.user.username} le {self.created_at}"


class EstablishmentWebSession(models.Model):
    """Revocable, per-device web session for privileged G-Connect dashboards.

    Only the SHA-256 hash of a high-entropy bearer credential is persisted;
    the raw token is returned once upon login, never stored in Django's DB.
    Flutter continues to use the original DRF Token model independently.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="establishment_web_sessions")
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"], name="users_web_user_created_e3_idx")]

    @classmethod
    def issue(cls, user, request):
        import hashlib
        import secrets
        from datetime import timedelta
        from django.conf import settings

        now = timezone.now()
        raw_token = secrets.token_urlsafe(48)
        ttl = timedelta(hours=max(1, settings.ESTABLISHMENT_WEB_SESSION_HOURS))
        session = cls.objects.create(
            user=user, token_hash=hashlib.sha256(raw_token.encode("ascii")).hexdigest(),
            created_at=now, last_seen_at=now, expires_at=now + ttl,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        max_count = max(1, settings.ESTABLISHMENT_WEB_SESSION_MAX_DEVICES)
        stale = list(
            cls.objects.filter(user=user, revoked_at__isnull=True)
            .order_by("-created_at", "-id").values_list("pk", flat=True)[max_count:]
        )
        if stale:
            cls.objects.filter(pk__in=stale).update(revoked_at=now)
        return session, raw_token

    def revoke(self):
        if self.revoked_at is None:
            self.revoked_at = timezone.now()
            self.save(update_fields=["revoked_at"])

    def __str__(self):
        return f"Session web #{self.pk} de {self.user_id}"


class VerificationToken(models.Model):
    """
    Token OTP persistant en base (remplace le stockage en session Django,
    incompatible avec les clients mobiles qui ne maintiennent pas les cookies).
    Couvre deux usages : activation du compte (email_verification) et
    réinitialisation du mot de passe (password_reset).
    """
    PURPOSE_EMAIL = 'email_verification'
    PURPOSE_RESET = 'password_reset'
    PURPOSE_CHOICES = [
        (PURPOSE_EMAIL, 'Vérification email'),
        (PURPOSE_RESET, 'Réinitialisation mot de passe'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.CharField(max_length=6)
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [models.Index(fields=['user', 'purpose', 'used'])]

    @classmethod
    def create_otp(cls, user, purpose, ttl_minutes=15):
        import random
        cls.objects.filter(user=user, purpose=purpose, used=False).delete()
        token = str(random.randint(100000, 999999))
        expires_at = timezone.now() + timezone.timedelta(minutes=ttl_minutes)
        return cls.objects.create(user=user, token=token, purpose=purpose, expires_at=expires_at)

    @classmethod
    def verify(cls, user, token, purpose):
        try:
            obj = cls.objects.get(user=user, token=token, purpose=purpose, used=False)
        except cls.DoesNotExist:
            return None, "OTP invalide ou déjà utilisé."
        if timezone.now() > obj.expires_at:
            obj.delete()
            return None, "OTP expiré."
        obj.used = True
        obj.save(update_fields=['used'])
        return obj, None


class SearchHistory(models.Model):
    """
    Historique des recherches de l'utilisateur — alimente les suggestions
    "recherches récentes" de l'écran de recherche universelle. Une même
    requête (insensible à la casse) n'apparaît qu'une fois : re-rechercher
    un terme déjà présent remonte simplement sa date en tête de liste.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="search_history")
    query = models.CharField(max_length=150)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.user.username} a recherché « {self.query} »"

    @classmethod
    def record(cls, user, query):
        query = query.strip()
        if not query:
            return
        cls.objects.filter(user=user, query__iexact=query).delete()
        cls.objects.create(user=user, query=query)
        # Ne conserver que les 20 plus récentes par utilisateur.
        stale_ids = cls.objects.filter(user=user).order_by("-created_at").values_list("id", flat=True)[20:]
        if stale_ids:
            cls.objects.filter(id__in=list(stale_ids)).delete()

class EstablishmentInvitation(models.Model):
    """Single-use emailed invitation; activation also proves mailbox control."""

    email = models.EmailField(db_index=True)
    institution = models.ForeignKey(Institution, on_delete=models.PROTECT, related_name="admin_invitations")
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="sent_establishment_invitations")
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    accepted_user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="accepted_establishment_invitations"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email", "-created_at"], name="users_e4_inv_email_idx")]


class PrivilegedMFADevice(models.Model):
    """The TOTP seed is encrypted (Fernet), never stored as clear text."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="privileged_mfa")
    encrypted_secret = models.TextField(blank=True)
    setup_expires_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    last_used_step = models.BigIntegerField(default=-1)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class PrivilegedAuthChallenge(models.Model):
    KIND_ENROLL = "enroll"
    KIND_VERIFY = "verify"
    KIND_CHOICES = [(KIND_ENROLL, "Enroll"), (KIND_VERIFY, "Verify")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="privileged_challenges")
    token_hash = models.CharField(max_length=64, unique=True)
    kind = models.CharField(max_length=8, choices=KIND_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["user", "-created_at"], name="users_e4_ch_user_idx")]


class PrivilegedRecoveryCode(models.Model):
    """One-time recovery secrets (the raw codes are shown only upon enrollment)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="privileged_recovery_codes")
    code_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "used_at"], name="users_e4_rec_user_idx")]
