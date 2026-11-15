"""
Management command: fix_memberships

Diagnostique et répare les données manquantes qui empêchent la section
"Membres" de la home page de fonctionner :

  1. Vérifie que chaque établissement a bien une promotion générale (is_general=True).
  2. Vérifie que chaque étudiant a un PromotionMembership approuvé dans la
     promotion générale de son établissement.
  3. Vérifie que chaque utilisateur de role 'etablissement' a un InstitutionAdmin
     et affiche son institution_id.

Usage :
  python manage.py fix_memberships          # diagnostic seulement
  python manage.py fix_memberships --fix    # répare les données manquantes
"""

from django.core.management.base import BaseCommand
from apps.api.v1.establishments.models import (
    Institution, Promotion, PromotionMembership, StudentInstitution,
)
from apps.api.v1.users.models import User, InstitutionAdmin


class Command(BaseCommand):
    help = 'Diagnostique et répare les memberships manquants pour la home page'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Appliquer les réparations (sans ce flag, mode diagnostic uniquement)',
        )

    def handle(self, *args, **options):
        fix = options['fix']
        mode = 'RÉPARATION' if fix else 'DIAGNOSTIC'
        self.stdout.write(self.style.WARNING(f'\n=== {mode} DES MEMBERSHIPS ===\n'))

        # ── 1. Promotions générales ───────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('1. Promotions générales par établissement'))
        institutions = Institution.objects.all()
        for inst in institutions:
            general = inst.general_promotion
            if general:
                count = PromotionMembership.objects.filter(
                    promotion=general, is_approved=True
                ).count()
                self.stdout.write(
                    f'   ✅ {inst.name} → "{general.name}" ({count} membres approuvés)'
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'   ❌ {inst.name} → AUCUNE promotion générale')
                )
                if fix:
                    promo = Promotion.objects.create(
                        name=f'Promotion Générale - {inst.name}',
                        institution=inst,
                        is_general=True,
                        description=f'Promotion générale de tous les membres de {inst.name}',
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'      → Créée : "{promo.name}"')
                    )

        # ── 2. Memberships étudiants ──────────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('\n2. Memberships étudiants manquants'))
        sis = StudentInstitution.objects.select_related(
            'student__user', 'institution'
        ).all()
        missing = 0
        for si in sis:
            general = si.institution.general_promotion
            if not general:
                continue
            has = PromotionMembership.objects.filter(
                student=si.student, promotion=general
            ).exists()
            if not has:
                missing += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'   ⚠️  {si.student.user.username} n\'a pas de membership '
                        f'dans "{general.name}"'
                    )
                )
                if fix:
                    PromotionMembership.objects.create(
                        student=si.student,
                        promotion=general,
                        is_approved=True,
                    )
                    self.stdout.write(self.style.SUCCESS('      → Membership créé'))

        if missing == 0:
            self.stdout.write('   ✅ Aucun membership manquant')

        # ── 3. Utilisateurs établissement ─────────────────────────────────────
        self.stdout.write(self.style.HTTP_INFO('\n3. Utilisateurs "etablissement"'))
        admins = User.objects.filter(role='etablissement')
        for user in admins:
            try:
                admin_profile = user.institution_admin_profile
                self.stdout.write(
                    f'   ✅ {user.username} → institution_id={admin_profile.institution_id} '
                    f'("{admin_profile.institution.name}")'
                )
            except InstitutionAdmin.RelatedObjectDoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f'   ❌ {user.username} → PAS de InstitutionAdmin lié\n'
                        f'      Créer manuellement via admin Django :\n'
                        f'      InstitutionAdmin(user_id={user.id}, institution=<votre institution>)'
                    )
                )

        self.stdout.write(self.style.SUCCESS('\n=== TERMINÉ ===\n'))
        if not fix:
            self.stdout.write(
                self.style.WARNING('Relancez avec --fix pour appliquer les réparations.\n')
            )
