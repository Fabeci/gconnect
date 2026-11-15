"""Install the approved G-Connect one-month reference prices without altering live rates.

Usage:
  python manage.py seed_subscription_baseline --settings=gconnect_api.settings.dev
  python manage.py seed_subscription_baseline --apply --settings=gconnect_api.settings.dev

The preview is read-only. --apply creates *missing* active monthly prices only.
It never reprices an existing offer, retires a price, or changes subscriptions.
"""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.api.v1.subscriptions.models import CommercialOffer, PriceOption


BASELINE = (
    (100, Decimal("30000.00")),
    (200, Decimal("50000.00")),
    (500, Decimal("100000.00")),
    (1000, Decimal("180000.00")),
)


class Command(BaseCommand):
    help = "Prévisualiser ou ajouter les prix mensuels de référence G-Connect (XOF)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Créer uniquement les paliers mensuels absents. Sans cette option : lecture seule.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]
        with transaction.atomic():
            offer = CommercialOffer.objects.filter(slug="offre-par-compte").first()
            if offer is None:
                raise CommandError("Offre par compte introuvable : appliquer les migrations E22.")
            if offer.kind != CommercialOffer.Kind.PER_ACCOUNT:
                raise CommandError("Le modèle de l'offre par compte n'est pas conforme.")
            if not offer.is_active:
                raise CommandError("Offre par compte inactive : aucune modification autorisée.")

            created = 0
            for seats, amount in BASELINE:
                existing = PriceOption.objects.filter(
                    offer=offer, term_months=PriceOption.Term.MONTHLY,
                    seats=seats, is_active=True,
                ).first()
                if existing is not None:
                    self.stdout.write(
                        f"CONSERVÉ {seats} comptes : {existing.amount} {existing.currency} "
                        "(prix actif déjà configuré)"
                    )
                    continue
                self.stdout.write(
                    f"{'CRÉATION' if apply else 'À CRÉER'} "
                    f"{seats} comptes / 1 mois : {amount:.0f} XOF"
                )
                if apply:
                    option = PriceOption(
                        offer=offer, term_months=PriceOption.Term.MONTHLY,
                        seats=seats, amount=amount, currency="XOF",
                    )
                    option.full_clean(exclude=["created_by"])
                    option.save()
                    created += 1
            if apply:
                self.stdout.write(self.style.SUCCESS(
                    f"{created} tarif(s) créé(s) ; aucun tarif existant remplacé."
                ))
            else:
                self.stdout.write(
                    "APERÇU UNIQUEMENT. Relancer avec --apply pour enregistrer les paliers absents."
                )
            self.stdout.write(
                "Non inclus : 6/12 mois (tarifs à fixer), sur devis, "
                "illimité, étudiant et entreprise individuelle."
            )
