"""E38 · Issued invoices, scoped to real provider-verified checkouts.

Only invoices are accounting documents. Subscription assignments remain distinct.
All printed terms are immutable snapshots, protecting against later price edits.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q


class InvoiceIssuerProfile(models.Model):
    """One legal issuer (pk=1). No values are assumed for tax and legal details."""
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    legal_name = models.CharField(max_length=200, blank=True)
    registration_number = models.CharField(max_length=90, blank=True)
    tax_identifier = models.CharField(max_length=90, blank=True)
    address = models.TextField(blank=True)
    country_code = models.CharField(max_length=2, blank=True)
    email = models.EmailField(blank=True)
    invoice_prefix = models.CharField(max_length=10, default="GC")
    tax_treatment = models.CharField(max_length=20, blank=True, choices=[
        ("included", "Taxe comprise dans le prix"),
        ("exempt", "Exonération ou absence de taxe légalement applicable"),
    ])
    tax_label = models.CharField(max_length=50, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    exemption_reason = models.CharField(max_length=250, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk != 1:
            raise ValueError("Une seule identité légale émettrice est autorisée.")
        super().save(*args, **kwargs)


class InvoiceSequence(models.Model):
    """Per-year monotonic counter, allocated in a database transaction."""
    year = models.PositiveSmallIntegerField(primary_key=True)
    last_number = models.PositiveIntegerField(default=0)


class IssuedInvoice(models.Model):
    """Immutable issued document for one confirmed payment; no demo invoice."""
    id = models.BigAutoField(primary_key=True)
    checkout = models.OneToOneField(
        "subscriptions.SubscriptionCheckout", on_delete=models.PROTECT,
        related_name="issued_invoice",
    )
    subscription = models.ForeignKey(
        "subscriptions.BusinessSubscription", on_delete=models.PROTECT,
        related_name="issued_invoices",
    )
    number = models.CharField(max_length=30, unique=True)
    year = models.PositiveSmallIntegerField()
    sequence_number = models.PositiveIntegerField()
    issuer_snapshot = models.JSONField()
    customer_snapshot = models.JSONField()
    sale_snapshot = models.JSONField()
    amount_net = models.DecimalField(max_digits=12, decimal_places=2)
    amount_tax = models.DecimalField(max_digits=12, decimal_places=2)
    amount_total = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    issued_at = models.DateTimeField()
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
        related_name="invoices_issued",
    )

    class Meta:
        ordering = ["-issued_at", "-pk"]
        constraints = [
            models.UniqueConstraint(fields=["year", "sequence_number"], name="unique_invoice_year_number"),
            models.CheckConstraint(condition=Q(amount_total__gt=0), name="invoice_amount_positive"),
        ]
