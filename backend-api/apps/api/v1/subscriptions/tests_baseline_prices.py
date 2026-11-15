"""Reference pricing seed: dry-run, idempotency and protection of configured prices."""
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.api.v1.subscriptions.models import CommercialOffer, PriceOption


class ReferencePricingSeedTests(TestCase):
    def setUp(self):
        self.offer, _ = CommercialOffer.objects.get_or_create(
            slug="offre-par-compte",
            defaults={
                "name": "Offre par compte", "kind": "per_account",
                "audience": "all",
            },
        )

    def run_seed(self, *options):
        output = StringIO()
        call_command("seed_subscription_baseline", *options, stdout=output)
        return output.getvalue()

    def test_default_is_read_only_and_apply_adds_four_monthly_tiers(self):
        self.run_seed()
        self.assertFalse(PriceOption.objects.filter(offer=self.offer).exists())
        self.run_seed("--apply")
        amounts = dict(PriceOption.objects.filter(
            offer=self.offer, term_months=1, is_active=True,
        ).values_list("seats", "amount"))
        self.assertEqual(amounts, {
            100: Decimal("30000.00"), 200: Decimal("50000.00"),
            500: Decimal("100000.00"), 1000: Decimal("180000.00"),
        })
        self.run_seed("--apply")
        self.assertEqual(PriceOption.objects.filter(offer=self.offer).count(), 4)

    def test_existing_active_price_is_not_repriced(self):
        PriceOption.objects.create(
            offer=self.offer, term_months=1, seats=200,
            amount=Decimal("42000.00"), currency="XOF",
        )
        output = self.run_seed("--apply")
        self.assertIn("CONSERVÉ 200 comptes", output)
        self.assertEqual(
            PriceOption.objects.get(offer=self.offer, seats=200, term_months=1).amount,
            Decimal("42000.00"),
        )
        self.assertEqual(PriceOption.objects.filter(offer=self.offer).count(), 4)
