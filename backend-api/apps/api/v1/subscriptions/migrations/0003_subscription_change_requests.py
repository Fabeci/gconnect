"""Organisation-initiated renewal and capacity requests; no automatic payment or activation."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0002_organisation_quotas"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionChangeRequest",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("request_type", models.CharField(max_length=12, choices=[
                    ("renewal", "Renouvellement"), ("capacity", "Capacité supplémentaire"),
                ])),
                ("requested_term_months", models.PositiveSmallIntegerField(null=True, blank=True)),
                ("requested_quantity", models.PositiveIntegerField(null=True, blank=True)),
                ("note", models.CharField(max_length=500, blank=True)),
                ("status", models.CharField(max_length=20, default="pending", choices=[
                    ("pending", "En attente"), ("info_requested", "Précisions demandées"),
                    ("approved", "Accord de principe"), ("rejected", "Refusée"),
                ])),
                ("admin_note", models.CharField(max_length=500, blank=True)),
                ("reviewed_at", models.DateTimeField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(
                    to=settings.AUTH_USER_MODEL, null=True,
                    related_name="requested_subscription_changes",
                    on_delete=django.db.models.deletion.SET_NULL,
                )),
                ("reviewed_by", models.ForeignKey(
                    to=settings.AUTH_USER_MODEL, null=True, blank=True,
                    related_name="reviewed_subscription_changes",
                    on_delete=django.db.models.deletion.SET_NULL,
                )),
                ("institution", models.ForeignKey(
                    to="establishments.institution", null=True, blank=True,
                    related_name="subscription_change_requests",
                    on_delete=django.db.models.deletion.PROTECT,
                )),
                ("enterprise", models.ForeignKey(
                    to="users.enterprise", null=True, blank=True,
                    related_name="subscription_change_requests",
                    on_delete=django.db.models.deletion.PROTECT,
                )),
                ("source_subscription", models.ForeignKey(
                    to="subscriptions.businesssubscription", null=True, blank=True,
                    related_name="change_requests",
                    on_delete=django.db.models.deletion.PROTECT,
                )),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="subscriptionchangerequest",
            constraint=models.CheckConstraint(
                condition=(
                    Q(institution__isnull=False, enterprise__isnull=True)
                    | Q(institution__isnull=True, enterprise__isnull=False)
                ),
                name="request_one_organisation",
            ),
        ),
    ]
