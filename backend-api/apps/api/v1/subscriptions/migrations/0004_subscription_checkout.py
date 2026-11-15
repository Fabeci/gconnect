"""Versioned self-service checkout with one payment-verified contract per transaction."""
import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0003_subscription_change_requests"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="businesssubscription", name="status",
            field=models.CharField(max_length=12, default="active", choices=[
                ("active", "Actif"), ("ended", "Terminé"),
                ("suspended", "Suspendu"), ("scheduled", "Programmé"),
            ]),
        ),
        migrations.CreateModel(
            name="SubscriptionCheckout",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("transaction_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("offer_name", models.CharField(max_length=150)),
                ("capacity", models.PositiveIntegerField()),
                ("quota_unit", models.CharField(max_length=20, choices=[
                    ("accounts", "Comptes actifs"),
                    ("publications", "Publications consommées"),
                ])),
                ("term_months", models.PositiveSmallIntegerField()),
                ("amount", models.DecimalField(max_digits=12, decimal_places=2)),
                ("currency", models.CharField(max_length=3)),
                ("status", models.CharField(max_length=12, default="pending", choices=[
                    ("pending", "En attente de paiement"),
                    ("paid", "Payé et enregistré"),
                    ("failed", "Échec"), ("canceled", "Annulé"),
                ])),
                ("provider", models.CharField(default="cinetpay", max_length=20)),
                ("checkout_url", models.URLField(blank=True, max_length=850)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(
                    to=settings.AUTH_USER_MODEL, related_name="subscription_checkouts",
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                )),
                ("institution", models.ForeignKey(
                    to="establishments.institution", null=True, blank=True,
                    related_name="subscription_checkouts",
                    on_delete=django.db.models.deletion.PROTECT,
                )),
                ("enterprise", models.ForeignKey(
                    to="users.enterprise", null=True, blank=True,
                    related_name="subscription_checkouts",
                    on_delete=django.db.models.deletion.PROTECT,
                )),
                ("price_option", models.ForeignKey(
                    to="subscriptions.priceoption",
                    on_delete=django.db.models.deletion.PROTECT,
                )),
                ("source_subscription", models.ForeignKey(
                    to="subscriptions.businesssubscription", null=True, blank=True,
                    related_name="renewal_checkouts",
                    on_delete=django.db.models.deletion.PROTECT,
                )),
                ("activated_subscription", models.OneToOneField(
                    to="subscriptions.businesssubscription", null=True, blank=True,
                    related_name="verified_checkout",
                    on_delete=django.db.models.deletion.PROTECT,
                )),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="subscriptioncheckout",
            constraint=models.CheckConstraint(
                condition=(
                    Q(institution__isnull=False, enterprise__isnull=True)
                    | Q(institution__isnull=True, enterprise__isnull=False)
                ),
                name="checkout_one_organisation",
            ),
        ),
        migrations.AddConstraint(
            model_name="subscriptioncheckout",
            constraint=models.CheckConstraint(condition=Q(capacity__gte=1), name="checkout_capacity_positive"),
        ),
        migrations.AddConstraint(
            model_name="subscriptioncheckout",
            constraint=models.CheckConstraint(condition=Q(amount__gt=0), name="checkout_amount_positive"),
        ),
    ]
