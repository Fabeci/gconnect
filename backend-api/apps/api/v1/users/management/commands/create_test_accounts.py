from datetime import date

from django.core.management.base import BaseCommand

from apps.api.v1.users.models import User, Student, Alumni, InstitutionAdmin, Enterprise
from apps.api.v1.establishments.models import Institution, Promotion


PASSWORD = "Test@1234"

ACCOUNTS = [
    {
        "username": "superadmin",
        "email": "superadmin@gconnect.test",
        "first_name": "Super",
        "last_name": "Admin",
        "role": "superAdmin",
        "is_superuser": True,
        "is_staff": True,
    },
    {
        "username": "admin_etab",
        "email": "admin.etab@gconnect.test",
        "first_name": "Admin",
        "last_name": "Établissement",
        "role": "etablissement",
    },
    {
        "username": "etudiant",
        "email": "etudiant@gconnect.test",
        "first_name": "Jean",
        "last_name": "Étudiant",
        "role": "student",
    },
    {
        "username": "alumni",
        "email": "alumni@gconnect.test",
        "first_name": "Marie",
        "last_name": "Alumni",
        "role": "alumni",
    },
    {
        "username": "entreprise",
        "email": "entreprise@gconnect.test",
        "first_name": "Acme",
        "last_name": "Corp",
        "role": "enterprise",
    },
]


class Command(BaseCommand):
    help = "Crée des comptes de test activés pour chaque profil utilisateur"

    def handle(self, *args, **options):
        institution = self._get_or_create_institution()
        promotion = self._get_or_create_promotion(institution)

        for data in ACCOUNTS:
            self._create_account(data, institution, promotion)

        self.stdout.write(self.style.SUCCESS("\nComptes de test créés avec succès."))
        self.stdout.write(f"  Mot de passe commun : {PASSWORD}\n")

    def _get_or_create_institution(self):
        institution, created = Institution.objects.get_or_create(
            name="Université de Test",
            defaults={
                "acronym": "UDT",
                "is_active": True,
            },
        )
        if created:
            self.stdout.write(f"  [+] Institution créée : {institution.name}")
        else:
            self.stdout.write(f"  [=] Institution existante : {institution.name}")
        return institution

    def _get_or_create_promotion(self, institution):
        promotion, created = Promotion.objects.get_or_create(
            name="Promotion Générale",
            institution=institution,
            defaults={
                "year": 2024,
                "is_general": True,
            },
        )
        if created:
            self.stdout.write(f"  [+] Promotion créée : {promotion.name}")
        else:
            self.stdout.write(f"  [=] Promotion existante : {promotion.name}")
        return promotion

    def _create_account(self, data, institution, promotion):
        role = data["role"]
        email = data["email"]

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "username": data["username"],
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "role": role,
                "is_active": True,
                "is_superuser": data.get("is_superuser", False),
                "is_staff": data.get("is_staff", False),
            },
        )

        if created:
            user.set_password(PASSWORD)
            user.save()
            self._create_profile(user, role, institution, promotion)
            self.stdout.write(self.style.SUCCESS(f"  [+] {role:15s} -> {email}"))
        else:
            self.stdout.write(f"  [=] {role:15s} -> {email} (déjà existant)")

    def _create_profile(self, user, role, institution, promotion):
        if role == "student":
            Student.objects.get_or_create(
                user=user,
                defaults={
                    "gender": "M",
                    "date_of_birth": date(2000, 1, 1),
                    "student_id": f"STU-{user.pk:04d}",
                },
            )

        elif role == "alumni":
            Alumni.objects.get_or_create(
                user=user,
                defaults={
                    "gender": "F",
                    "graduation_date": date(2022, 6, 30),
                    "institution": institution,
                    "promotion": promotion,
                    "proof_document": "",
                },
            )

        elif role == "etablissement":
            InstitutionAdmin.objects.get_or_create(
                user=user,
                defaults={"institution": institution},
            )

        elif role == "enterprise":
            Enterprise.objects.get_or_create(
                user=user,
                defaults={
                    "company_name": "Acme Corp",
                    "sector": "Technologie",
                },
            )
