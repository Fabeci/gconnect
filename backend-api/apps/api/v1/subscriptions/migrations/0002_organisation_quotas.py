"""Add durable publication credits and extra capacity without changing existing contracts."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


def initialise_professional_offers(apps, schema_editor):
    Offer = apps.get_model("subscriptions", "CommercialOffer")
    Contract = apps.get_model("subscriptions", "BusinessSubscription")
    # Preserve historical amounts, dates, and capacity. Legacy enterprise
    # contracts receive publication credits for their remaining term, rather
    # than unexpectedly blocking clients who already hold an active contract.
    # Old publications are not retroactively consumed: the ledger begins here.
    Contract.objects.filter(enterprise__isnull=False).update(quota_unit="publications")
    # Existing price rows are deliberately left unchanged for audit history.
    for slug in ("offre-flexible", "offre-par-compte"):
        Offer.objects.filter(slug=slug, audience="all").update(audience="institution")
    Offer.objects.get_or_create(slug="offre-entreprise-publications", defaults={
        "name": "Offre Publications", "kind": "flexible",
        "audience": "enterprise", "quota_unit": "publications",
        "description": "Publiez un nombre défini d'offres pendant 1, 6 ou 12 mois.",
    })


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0001_initial"),
        ("posts", "0007_rename_posts_comme_comment_idx_posts_comme_comment_fb3e22_idx_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(
            model_name="commercialoffer", name="quota_unit",
            field=models.CharField(max_length=20, default="accounts", choices=[
                ("accounts", "Comptes actifs"), ("publications", "Publications consommées"),
            ]),
        ),
        migrations.AddField(
            model_name="businesssubscription", name="quota_unit",
            field=models.CharField(max_length=20, default="accounts", choices=[
                ("accounts", "Comptes actifs"), ("publications", "Publications consommées"),
            ]),
        ),
        migrations.CreateModel(
            name="PublicationConsumption",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("title_snapshot", models.CharField(max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("post", models.ForeignKey(
                    null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="subscription_consumptions", to="posts.post",
                )),
                ("subscription", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="publication_consumptions", to="subscriptions.businesssubscription",
                )),
            ],
        ),
        migrations.AddConstraint(
            model_name="publicationconsumption",
            constraint=models.UniqueConstraint(
                fields=["post"], condition=Q(post__isnull=False),
                name="unique_publication_credit_per_post",
            ),
        ),
        migrations.CreateModel(
            name="SubscriptionTopUp",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("quantity", models.PositiveIntegerField()),
                ("amount", models.DecimalField(max_digits=12, decimal_places=2)),
                ("currency", models.CharField(max_length=3)),
                ("note", models.CharField(max_length=255, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
                ("subscription", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="top_ups", to="subscriptions.businesssubscription",
                )),
            ],
        ),
        migrations.AddConstraint(
            model_name="subscriptiontopup",
            constraint=models.CheckConstraint(condition=Q(quantity__gte=1), name="topup_quantity_positive"),
        ),
        migrations.AddConstraint(
            model_name="subscriptiontopup",
            constraint=models.CheckConstraint(condition=Q(amount__gte=0), name="topup_amount_nonnegative"),
        ),
        migrations.RunPython(initialise_professional_offers, migrations.RunPython.noop),
    ]
