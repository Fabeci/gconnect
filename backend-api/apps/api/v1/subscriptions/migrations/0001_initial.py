"""First commercial subscription tables. Existing users and subscription-free accounts are preserved."""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


def create_offer_families(apps, schema_editor):
    Offer = apps.get_model("subscriptions", "CommercialOffer")
    Offer.objects.get_or_create(slug="offre-flexible", defaults={
        "name": "Offre Flexible", "kind": "flexible", "audience": "all",
        "description": "Tarifs configurés par durée et capacité.",
    })
    Offer.objects.get_or_create(slug="offre-par-compte", defaults={
        "name": "Offre par compte", "kind": "per_account", "audience": "all",
        "description": "Chaque combinaison de comptes et de durée a son propre tarif.",
    })


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("establishments", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="CommercialOffer",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("slug", models.SlugField(max_length=100, unique=True)),
                ("name", models.CharField(max_length=150)),
                ("description", models.CharField(blank=True, max_length=500)),
                ("kind", models.CharField(max_length=20, choices=[
                    ("flexible", "Offre Flexible"), ("per_account", "Offre par compte"),
                ])),
                ("audience", models.CharField(max_length=20, default="all", choices=[
                    ("all", "Établissements et entreprises"),
                    ("institution", "Établissements"), ("enterprise", "Entreprises"),
                ])),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["kind", "name"]},
        ),
        migrations.CreateModel(
            name="PriceOption",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("term_months", models.PositiveSmallIntegerField(choices=[
                    (0, "Sur devis"), (1, "1 mois"), (6, "6 mois"), (12, "12 mois"),
                ])),
                ("seats", models.PositiveIntegerField()),
                ("amount", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("currency", models.CharField(default="XOF", max_length=3)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("offer", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="price_options", to="subscriptions.commercialoffer",
                )),
                ("created_by", models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["offer_id", "term_months", "seats", "-created_at"]},
        ),
        migrations.CreateModel(
            name="BusinessSubscription",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("offer_name", models.CharField(max_length=150)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("currency", models.CharField(max_length=3)),
                ("seats", models.PositiveIntegerField()),
                ("term_months", models.PositiveSmallIntegerField()),
                ("starts_at", models.DateField()),
                ("ends_at", models.DateField()),
                ("status", models.CharField(max_length=12, default="active", choices=[
                    ("active", "Actif"), ("ended", "Terminé"), ("suspended", "Suspendu"),
                ])),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("price_option", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT, to="subscriptions.priceoption",
                )),
                ("institution", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="commercial_subscriptions", to="establishments.institution",
                )),
                ("enterprise", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                    related_name="commercial_subscriptions", to="users.enterprise",
                )),
                ("created_by", models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ["-created_at", "-id"]},
        ),
        migrations.AddConstraint(
            model_name="priceoption", constraint=models.UniqueConstraint(
                fields=["offer", "term_months", "seats"],
                condition=Q(is_active=True), name="uniq_live_offer_term_seats",
            ),
        ),
        migrations.AddConstraint(
            model_name="priceoption", constraint=models.CheckConstraint(
                condition=Q(seats__gte=1), name="pricing_seats_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="priceoption", constraint=models.CheckConstraint(
                condition=Q(amount__gte=0) | Q(amount__isnull=True), name="pricing_amount_positive",
            ),
        ),
        migrations.AddConstraint(
            model_name="businesssubscription", constraint=models.CheckConstraint(
                condition=(
                    Q(institution__isnull=False, enterprise__isnull=True) |
                    Q(institution__isnull=True, enterprise__isnull=False)
                ),
                name="subscription_one_organisation",
            ),
        ),
        migrations.AddConstraint(
            model_name="businesssubscription", constraint=models.UniqueConstraint(
                fields=["institution"], condition=Q(status="active", institution__isnull=False),
                name="unique_active_institution_subscription",
            ),
        ),
        migrations.AddConstraint(
            model_name="businesssubscription", constraint=models.UniqueConstraint(
                fields=["enterprise"], condition=Q(status="active", enterprise__isnull=False),
                name="unique_active_enterprise_subscription",
            ),
        ),
        migrations.RunPython(create_offer_families, migrations.RunPython.noop),
    ]
