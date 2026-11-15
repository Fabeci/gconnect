"""E38: invoice issuer, numbering and immutable snapshots."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0004_subscription_checkout"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="InvoiceIssuerProfile",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("legal_name", models.CharField(blank=True, max_length=200)),
                ("registration_number", models.CharField(blank=True, max_length=90)),
                ("tax_identifier", models.CharField(blank=True, max_length=90)),
                ("address", models.TextField(blank=True)),
                ("country_code", models.CharField(blank=True, max_length=2)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("invoice_prefix", models.CharField(default="GC", max_length=10)),
                ("tax_treatment", models.CharField(blank=True, choices=[
                    ("included", "Taxe comprise dans le prix"),
                    ("exempt", "Exonération ou absence de taxe légalement applicable"),
                ], max_length=20)),
                ("tax_label", models.CharField(blank=True, max_length=50)),
                ("tax_rate", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("exemption_reason", models.CharField(blank=True, max_length=250)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="InvoiceSequence",
            fields=[
                ("year", models.PositiveSmallIntegerField(primary_key=True, serialize=False)),
                ("last_number", models.PositiveIntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name="IssuedInvoice",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("number", models.CharField(max_length=30, unique=True)),
                ("year", models.PositiveSmallIntegerField()),
                ("sequence_number", models.PositiveIntegerField()),
                ("issuer_snapshot", models.JSONField()),
                ("customer_snapshot", models.JSONField()),
                ("sale_snapshot", models.JSONField()),
                ("amount_net", models.DecimalField(decimal_places=2, max_digits=12)),
                ("amount_tax", models.DecimalField(decimal_places=2, max_digits=12)),
                ("amount_total", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(max_length=3)),
                ("issued_at", models.DateTimeField()),
                ("checkout", models.OneToOneField(
                    on_delete=django.db.models.deletion.PROTECT, related_name="issued_invoice",
                    to="subscriptions.subscriptioncheckout")),
                ("subscription", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, related_name="issued_invoices",
                    to="subscriptions.businesssubscription")),
                ("issued_by", models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="invoices_issued", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-issued_at", "-pk"], "constraints": [
                models.UniqueConstraint(fields=("year", "sequence_number"), name="unique_invoice_year_number"),
                models.CheckConstraint(condition=Q(amount_total__gt=0), name="invoice_amount_positive"),
            ]},
        ),
    ]
