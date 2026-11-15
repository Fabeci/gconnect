"""Configurable commercial offers, versioned prices and immutable subscription snapshots."""
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class CommercialOffer(models.Model):
    # Matches the explicit primary key declared by the original E22 migration.
    id = models.BigAutoField(primary_key=True)
    class QuotaUnit(models.TextChoices):
        ACCOUNTS = "accounts", "Comptes actifs"
        PUBLICATIONS = "publications", "Publications consommées"

    class Kind(models.TextChoices):
        FLEXIBLE = "flexible", "Offre Flexible"
        PER_ACCOUNT = "per_account", "Offre par compte"

    class Audience(models.TextChoices):
        ALL = "all", "Établissements et entreprises"
        INSTITUTION = "institution", "Établissements"
        ENTERPRISE = "enterprise", "Entreprises"

    slug = models.SlugField(unique=True, max_length=100)
    name = models.CharField(max_length=150)
    description = models.CharField(max_length=500, blank=True)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ALL)
    quota_unit = models.CharField(max_length=20, choices=QuotaUnit.choices, default=QuotaUnit.ACCOUNTS)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kind", "name"]

    def __str__(self):
        return self.name


class PriceOption(models.Model):
    """Active price combinations are unique; superseded rows remain for audit/history."""
    id = models.BigAutoField(primary_key=True)
    class Term(models.IntegerChoices):
        QUOTE = 0, "Sur devis"
        MONTHLY = 1, "1 mois"
        SEMESTER = 6, "6 mois"
        ANNUAL = 12, "12 mois"

    offer = models.ForeignKey(CommercialOffer, related_name="price_options", on_delete=models.PROTECT)
    term_months = models.PositiveSmallIntegerField(choices=Term.choices)
    seats = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="XOF")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["offer_id", "term_months", "seats", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["offer", "term_months", "seats"],
                condition=Q(is_active=True),
                name="uniq_live_offer_term_seats",
            ),
            models.CheckConstraint(condition=Q(seats__gte=1), name="pricing_seats_positive"),
            models.CheckConstraint(
                condition=Q(amount__gte=0) | Q(amount__isnull=True),
                name="pricing_amount_positive",
            ),
        ]

    def clean(self):
        if self.term_months not in (0, 1, 6, 12):
            raise ValidationError({"term_months": "Durée invalide."})
        if self.seats is None or self.seats < 1:
            raise ValidationError({"seats": "Au moins un compte est nécessaire."})
        if self.term_months == 0 and self.amount is not None:
            raise ValidationError({"amount": "Le montant sur devis est fixé lors de l'attribution."})
        if self.term_months != 0 and self.amount is None:
            raise ValidationError({"amount": "Montant obligatoire pour un forfait standard."})
        if self.amount is not None and self.amount < 0:
            raise ValidationError({"amount": "Montant négatif interdit."})


class BusinessSubscription(models.Model):
    """A confirmed manual activation; no payment is claimed or synthesized."""
    id = models.BigAutoField(primary_key=True)
    class State(models.TextChoices):
        ACTIVE = "active", "Actif"
        ENDED = "ended", "Terminé"
        SUSPENDED = "suspended", "Suspendu"
        SCHEDULED = "scheduled", "Programmé"

    price_option = models.ForeignKey(PriceOption, on_delete=models.PROTECT)
    institution = models.ForeignKey(
        "establishments.Institution", null=True, blank=True,
        related_name="commercial_subscriptions", on_delete=models.PROTECT,
    )
    enterprise = models.ForeignKey(
        "users.Enterprise", null=True, blank=True,
        related_name="commercial_subscriptions", on_delete=models.PROTECT,
    )
    # These are immutable billing terms, independent of later price edits.
    offer_name = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    seats = models.PositiveIntegerField()
    # Immutable quota type, even if the commercial offer is later edited.
    quota_unit = models.CharField(
        max_length=20, choices=CommercialOffer.QuotaUnit.choices,
        default=CommercialOffer.QuotaUnit.ACCOUNTS,
    )
    term_months = models.PositiveSmallIntegerField()
    starts_at = models.DateField()
    ends_at = models.DateField()
    status = models.CharField(max_length=12, choices=State.choices, default=State.ACTIVE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(institution__isnull=False, enterprise__isnull=True) |
                    Q(institution__isnull=True, enterprise__isnull=False)
                ),
                name="subscription_one_organisation",
            ),
            models.UniqueConstraint(
                fields=["institution"], condition=Q(status="active", institution__isnull=False),
                name="unique_active_institution_subscription",
            ),
            models.UniqueConstraint(
                fields=["enterprise"], condition=Q(status="active", enterprise__isnull=False),
                name="unique_active_enterprise_subscription",
            ),
        ]

    def clean(self):
        if bool(self.institution_id) == bool(self.enterprise_id):
            raise ValidationError("Un abonnement appartient à une seule organisation.")
        if self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "La fin doit être après le début."})


class PublicationConsumption(models.Model):
    """Append-only credit ledger. Deleting a published post never refunds the credit."""
    id = models.BigAutoField(primary_key=True)
    subscription = models.ForeignKey(
        BusinessSubscription, related_name="publication_consumptions", on_delete=models.PROTECT,
    )
    post = models.ForeignKey(
        "posts.Post", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="subscription_consumptions",
    )
    title_snapshot = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["post"], condition=Q(post__isnull=False),
                name="unique_publication_credit_per_post",
            ),
        ]


class SubscriptionTopUp(models.Model):
    """Manually granted extra quota, never misrepresented as an online payment."""
    id = models.BigAutoField(primary_key=True)
    subscription = models.ForeignKey(
        BusinessSubscription, related_name="top_ups", on_delete=models.PROTECT,
    )
    quantity = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="topup_quantity_positive"),
            models.CheckConstraint(condition=Q(amount__gte=0), name="topup_amount_nonnegative"),
        ]




class SubscriptionChangeRequest(models.Model):
    """Organisation-initiated request. Decisions never imply payment or automatic activation."""
    class RequestType(models.TextChoices):
        RENEWAL = "renewal", "Renouvellement"
        CAPACITY = "capacity", "Capacité supplémentaire"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        INFO_REQUESTED = "info_requested", "Précisions demandées"
        APPROVED = "approved", "Accord de principe"
        REJECTED = "rejected", "Refusée"

    id = models.BigAutoField(primary_key=True)
    institution = models.ForeignKey(
        "establishments.Institution", null=True, blank=True,
        on_delete=models.PROTECT, related_name="subscription_change_requests",
    )
    enterprise = models.ForeignKey(
        "users.Enterprise", null=True, blank=True,
        on_delete=models.PROTECT, related_name="subscription_change_requests",
    )
    source_subscription = models.ForeignKey(
        BusinessSubscription, null=True, blank=True, on_delete=models.PROTECT,
        related_name="change_requests",
    )
    request_type = models.CharField(max_length=12, choices=RequestType.choices)
    requested_term_months = models.PositiveSmallIntegerField(null=True, blank=True)
    requested_quantity = models.PositiveIntegerField(null=True, blank=True)
    note = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    admin_note = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
        related_name="requested_subscription_changes",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="reviewed_subscription_changes",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(institution__isnull=False, enterprise__isnull=True)
                    | Q(institution__isnull=True, enterprise__isnull=False)
                ),
                name="request_one_organisation",
            ),
        ]

    def clean(self):
        if bool(self.institution_id) == bool(self.enterprise_id):
            raise ValidationError("Une demande appartient à une seule organisation.")
        if self.request_type == self.RequestType.RENEWAL:
            if self.requested_term_months not in (1, 6, 12) or self.requested_quantity is not None:
                raise ValidationError("Renouvellement : durée de 1, 6 ou 12 mois obligatoire.")
        elif self.request_type == self.RequestType.CAPACITY:
            if not self.requested_quantity or self.requested_quantity < 1 or self.requested_term_months is not None:
                raise ValidationError("Extension : quantité strictement positive obligatoire.")
        else:
            raise ValidationError("Type de demande inconnu.")
        if self.source_subscription_id:
            expected_id = self.institution_id or self.enterprise_id
            source_id = (
                self.source_subscription.institution_id if self.institution_id
                else self.source_subscription.enterprise_id
            )
            if source_id != expected_id:
                raise ValidationError("Le contrat ne correspond pas à cette organisation.")



class SubscriptionCheckout(models.Model):
    """Immutable quote and external payment verification. No card data stored."""
    class Status(models.TextChoices):
        PENDING = "pending", "En attente de paiement"
        PAID = "paid", "Payé et enregistré"
        FAILED = "failed", "Échec"
        CANCELED = "canceled", "Annulé"

    id = models.BigAutoField(primary_key=True)
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    institution = models.ForeignKey(
        "establishments.Institution", null=True, blank=True,
        related_name="subscription_checkouts", on_delete=models.PROTECT,
    )
    enterprise = models.ForeignKey(
        "users.Enterprise", null=True, blank=True,
        related_name="subscription_checkouts", on_delete=models.PROTECT,
    )
    price_option = models.ForeignKey(PriceOption, on_delete=models.PROTECT)
    source_subscription = models.ForeignKey(
        BusinessSubscription, null=True, blank=True, on_delete=models.PROTECT,
        related_name="renewal_checkouts",
    )
    activated_subscription = models.OneToOneField(
        BusinessSubscription, null=True, blank=True, on_delete=models.PROTECT,
        related_name="verified_checkout",
    )
    offer_name = models.CharField(max_length=150)
    capacity = models.PositiveIntegerField()
    quota_unit = models.CharField(max_length=20, choices=CommercialOffer.QuotaUnit.choices)
    term_months = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=20, default="cinetpay")
    checkout_url = models.URLField(max_length=850, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
        related_name="subscription_checkouts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(institution__isnull=False, enterprise__isnull=True)
                    | Q(institution__isnull=True, enterprise__isnull=False)
                ),
                name="checkout_one_organisation",
            ),
            models.CheckConstraint(condition=Q(capacity__gte=1), name="checkout_capacity_positive"),
            models.CheckConstraint(condition=Q(amount__gt=0), name="checkout_amount_positive"),
        ]

    def clean(self):
        if bool(self.institution_id) == bool(self.enterprise_id):
            raise ValidationError("Une commande appartient à une seule organisation.")
        if self.term_months not in (1, 6, 12):
            raise ValidationError("Un paiement direct nécessite une durée fixe.")


# E38: keep invoicing models in their own module while registering them in Django.
from .invoice_models import InvoiceIssuerProfile, InvoiceSequence, IssuedInvoice  # noqa: E402,F401
