"""Create three local professional reference accounts safely.

This command never provisions MFA directly: the normal web-login enrollment flow
generates and confirms TOTP and returns one-time recovery codes to the user.
"""
from getpass import getpass
import sys

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.api.v1.establishments.models import Institution
from apps.api.v1.users.models import Enterprise, InstitutionAdmin, User


ACCOUNTS = (
    ("superadmin@gconnect.com", "superAdmin"),
    ("admin@etalissement.com", "etablissement"),
    ("admin@entreprise.com", "enterprise"),
)


class Command(BaseCommand):
    help = "Interactively create the three local G-Connect professional reference accounts."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Commande réservée à l'environnement local DEBUG.")
        if not sys.stdin.isatty():
            raise CommandError("Exécuter dans un terminal interactif.")
        existing = list(
            User.objects.filter(email__in=[email for email, _ in ACCOUNTS])
            .values_list("email", flat=True)
        )
        if existing:
            raise CommandError(
                "Compte(s) déjà présent(s) : " + ", ".join(existing)
                + ". Arrêt pour ne pas écraser de compte."
            )

        institutions = list(
            Institution.objects.filter(is_active=True).order_by("name")
            .values_list("pk", "name")
        )
        if not institutions:
            raise CommandError("Aucun établissement actif. Création annulée.")
        self.stdout.write("Établissements disponibles :")
        for pk, name in institutions:
            self.stdout.write(f"  {pk} : {name}")
        institution_id = input("ID de l'établissement à rattacher : ").strip()
        valid_ids = {str(pk) for pk, _ in institutions}
        if institution_id not in valid_ids:
            raise CommandError("ID d'établissement invalide. Aucune modification.")

        company_name = input("Nom de l'entreprise de référence : ").strip()
        sector = input("Secteur d'activité : ").strip()
        if not company_name or not sector:
            raise CommandError("Nom et secteur d'entreprise obligatoires.")

        passwords = {}
        for email, role in ACCOUNTS:
            self.stdout.write(f"\\nMot de passe pour {email} ({role})")
            password = getpass("Mot de passe : ")
            repeated = getpass("Confirmation : ")
            if password != repeated:
                raise CommandError("Confirmation incorrecte. Aucun compte créé.")
            candidate = User(username=email, email=email, role=role, is_active=True)
            try:
                validate_password(password, user=candidate)
            except ValidationError as exc:
                raise CommandError(
                    "Mot de passe non conforme : " + "; ".join(exc.messages)
                ) from exc
            passwords[email] = password

        confirmation = input("Créer ces 3 comptes sur CETTE base ? Tapez OUI : ").strip()
        if confirmation != "OUI":
            raise CommandError("Annulé. Aucune modification.")

        with transaction.atomic():
            # Recheck inside transaction, including case-insensitive duplicates.
            for email, _ in ACCOUNTS:
                if User.objects.filter(email__iexact=email).exists():
                    raise CommandError("Compte déjà existant : " + email)
            created = {}
            for email, role in ACCOUNTS:
                created[role] = User.objects.create_user(
                    username=email, email=email, role=role,
                    password=passwords[email], is_active=True,
                )
            InstitutionAdmin.objects.create(
                user=created["etablissement"], institution_id=int(institution_id),
            )
            Enterprise.objects.create(
                user=created["enterprise"], company_name=company_name, sector=sector,
                verified_at=timezone.now(),  # Explicit local operator provisioning.
            )

        self.stdout.write(self.style.SUCCESS(
            "Trois comptes et leurs profils créés. Aucun autre utilisateur modifié."
        ))
        self.stdout.write(
            "Ouvrez /superadmin, /etablissement et /entreprise et connectez-vous. "
            "La première connexion lance la configuration 2FA. "
            "Confirmez votre application TOTP puis sauvegardez les codes de secours "
            "affichés une seule fois, hors de GitHub et du terminal partagé."
        )
