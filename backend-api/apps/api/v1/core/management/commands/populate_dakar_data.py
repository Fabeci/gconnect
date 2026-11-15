"""
Management Command pour peupler la base de données avec des données du contexte de Dakar
Usage: python manage.py populate_dakar_data
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
import random

from apps.api.v1.core.models import Skill, Preference, Sector, Interest
from apps.api.v1.establishments.models import Institution, Promotion
from apps.api.v1.users.models import Student, Alumni, Enterprise, InstitutionAdmin
from apps.api.v1.posts.models import Post, Opportunity, Event, Project
from apps.api.v1.messaging.models import Conversation, ConversationParticipant, Message

User = get_user_model()


class Command(BaseCommand):
    help = 'Peuple la base de données avec des données du contexte de Dakar'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Début du peuplement de la base de données...'))
        
        # 1. Peupler les données de base
        self.populate_core_data()
        
        # 2. Créer les institutions de Dakar
        institutions = self.create_institutions()
        
        # 3. Créer les utilisateurs
        users = self.create_users(institutions)
        
        # 4. Créer les posts et opportunités
        self.create_posts(users, institutions)
        
        # 5. Créer les conversations
        self.create_conversations(users)
        
        self.stdout.write(self.style.SUCCESS('Peuplement terminé avec succès!'))

    def populate_core_data(self):
        """Peupler les compétences, préférences, secteurs et intérêts"""
        self.stdout.write('Peuplement des données de base...')
        
        # Compétences supplémentaires
        skills_data = [
            'Développement Web', 'Développement Mobile', 'DevOps', 'Cloud Computing',
            'Machine Learning', 'Big Data', 'Sécurité informatique', 'Réseaux',
            'Comptabilité', 'Finance', 'Ressources humaines', 'Logistique',
            'Agriculture urbaine', 'Pêche', 'Transformation alimentaire',
            'Tourisme', 'Hôtellerie', 'Transport maritime', 'Énergie solaire',
            'Gestion des déchets', 'Construction', 'Architecture', 'Design graphique',
            'Photographie', 'Vidéographie', 'Journalisme', 'Communication digitale',
            'Vente', 'Négociation', 'Service client', 'Gestion de stock'
        ]
        
        for skill_name in skills_data:
            Skill.objects.get_or_create(name=skill_name)
        
        # Préférences supplémentaires
        preferences_data = [
            'Travail en présentiel', 'Travail hybride', 'Startup', 'Grande entreprise',
            'Secteur public', 'ONG', 'Freelance', 'Entrepreneuriat',
            'Formation continue', 'Mentorat', 'Réseautage', 'International'
        ]
        
        for pref_name in preferences_data:
            Preference.objects.get_or_create(name=pref_name)
        
        # Secteurs spécifiques au Sénégal
        sectors_data = [
            'Pêche et Aquaculture', 'Agriculture et Élevage', 'Agroalimentaire',
            'BTP et Construction', 'Mines et Géologie', 'Énergie et Environnement',
            'Télécommunications', 'Banque et Assurance', 'Commerce et Distribution',
            'Transport et Logistique', 'Tourisme et Hôtellerie', 'Santé et Pharmacie',
            'Éducation et Formation', 'Culture et Arts', 'Sport et Loisirs',
            'Services aux entreprises', 'Administration publique', 'Développement durable'
        ]
        
        for sector_name in sectors_data:
            Sector.objects.get_or_create(name=sector_name)
        
        # Intérêts spécifiques au contexte
        interests_data = [
            'Développement local', 'Innovation sociale', 'Économie numérique',
            'Agriculture intelligente', 'Pêche durable', 'Énergie renouvelable',
            'Gestion des risques', 'Résilience climatique', 'Inclusion financière',
            'E-santé', 'E-gouvernance', 'Smart city', 'Mobilité urbaine',
            'Économie circulaire', 'Commerce équitable', 'Artisanat digital'
        ]
        
        for interest_name in interests_data:
            Interest.objects.get_or_create(name=interest_name)
        
        self.stdout.write(self.style.SUCCESS(f'  - {Skill.objects.count()} compétences'))
        self.stdout.write(self.style.SUCCESS(f'  - {Preference.objects.count()} préférences'))
        self.stdout.write(self.style.SUCCESS(f'  - {Sector.objects.count()} secteurs'))
        self.stdout.write(self.style.SUCCESS(f'  - {Interest.objects.count()} intérêts'))

    def create_institutions(self):
        """Créer les établissements d'enseignement de Dakar"""
        self.stdout.write('Création des institutions de Dakar...')
        
        institutions_data = [
            {
                'name': 'Université Cheikh Anta Diop de Dakar',
                'acronym': 'UCAD',
                'address': 'Avenue Cheikh Anta Diop, Dakar',
                'phone': '+221 33 825 03 55',
                'email': 'contact@ucad.sn',
                'website': 'https://www.ucad.sn',
                'established_year': 1957,
                'description': 'Plus grande université publique du Sénégal'
            },
            {
                'name': 'Université Gaston Berger de Saint-Louis',
                'acronym': 'UGB',
                'address': 'Saint-Louis, Sénégal',
                'phone': '+221 33 961 10 10',
                'email': 'contact@ugb.sn',
                'website': 'https://www.ugb.sn',
                'established_year': 1990,
                'description': 'Université publique réputée pour ses filières scientifiques'
            },
            {
                'name': 'École Supérieure Polytechnique de Dakar',
                'acronym': 'ESP',
                'address': 'Dakar, Sénégal',
                'phone': '+221 33 824 24 24',
                'email': 'contact@esp.sn',
                'website': 'https://www.esp.sn',
                'established_year': 1962,
                'description': 'École d\'ingénieurs de référence'
            },
            {
                'name': 'Institut Supérieur de Management',
                'acronym': 'ISM',
                'address': 'Dakar, Sénégal',
                'phone': '+221 33 849 50 50',
                'email': 'contact@ism.sn',
                'website': 'https://www.ism.sn',
                'established_year': 1997,
                'description': 'École de commerce et de gestion'
            },
            {
                'name': 'Université Assane Seck de Ziguinchor',
                'acronym': 'UASZ',
                'address': 'Ziguinchor, Sénégal',
                'phone': '+221 33 991 10 10',
                'email': 'contact@uasz.sn',
                'website': 'https://www.uasz.sn',
                'established_year': 2007,
                'description': 'Université publique de la Casamance'
            },
            {
                'name': 'École Nationale des Arts de Dakar',
                'acronym': 'ENART',
                'address': 'Dakar, Sénégal',
                'phone': '+221 33 822 22 22',
                'email': 'contact@enart.sn',
                'website': 'https://www.enart.sn',
                'established_year': 1960,
                'description': 'École d\'arts et de culture'
            },
            {
                'name': 'Institut de Technologie Alimentaire',
                'acronym': 'ITA',
                'address': 'Dakar, Sénégal',
                'phone': '+221 33 835 35 35',
                'email': 'contact@ita.sn',
                'website': 'https://www.ita.sn',
                'established_year': 1965,
                'description': 'Institut spécialisé dans l\'agroalimentaire'
            },
            {
                'name': 'École Nationale d\'Économie Appliquée',
                'acronym': 'ENEA',
                'address': 'Dakar, Sénégal',
                'phone': '+221 33 842 42 42',
                'email': 'contact@enea.sn',
                'website': 'https://www.enea.sn',
                'established_year': 1963,
                'description': 'École d\'économie et de statistique'
            }
        ]
        
        institutions = []
        for inst_data in institutions_data:
            institution, created = Institution.objects.get_or_create(
                acronym=inst_data['acronym'],
                defaults=inst_data
            )
            institutions.append(institution)
            if created:
                self.stdout.write(f'  - Créé: {institution.name}')
        
        self.stdout.write(self.style.SUCCESS(f'  - {len(institutions)} institutions'))
        return institutions

    def create_users(self, institutions):
        """Créer des utilisateurs (étudiants, alumni, entreprises, admins)"""
        self.stdout.write('Création des utilisateurs...')
        
        users = {
            'students': [],
            'alumni': [],
            'enterprises': [],
            'admins': []
        }
        
        # Créer un super admin
        superadmin, created = User.objects.get_or_create(
            email='admin@gconnect.sn',
            defaults={
                'username': 'superadmin',
                'first_name': 'Admin',
                'last_name': 'G-Connect',
                'role': 'superAdmin',
                'is_active': True,
                'is_staff': True,
                'is_superuser': True
            }
        )
        if created:
            superadmin.set_password('admin123')
            superadmin.save()
        
        # Créer des admins d'institution
        for i, institution in enumerate(institutions[:3]):
            admin_user, created = User.objects.get_or_create(
                email=f'admin.{institution.acronym.lower()}@{institution.acronym.lower()}.sn',
                defaults={
                    'username': f'admin_{institution.acronym.lower()}',
                    'first_name': f'Admin',
                    'last_name': institution.acronym,
                    'role': 'etablissement',
                    'is_active': True
                }
            )
            if created:
                admin_user.set_password('admin123')
                admin_user.save()
                InstitutionAdmin.objects.create(
                    user=admin_user,
                    institution=institution
                )
                users['admins'].append(admin_user)
        
        # Créer des entreprises
        enterprises_data = [
            {
                'company_name': 'Sonatel',
                'sector': 'Télécommunications',
                'website': 'https://www.sonatel.sn',
                'email': 'recrutement@sonatel.sn'
            },
            {
                'company_name': 'Sénélec',
                'sector': 'Énergie',
                'website': 'https://www.senelec.sn',
                'email': 'recrutement@senelec.sn'
            },
            {
                'company_name': 'Cosumar',
                'sector': 'Agroalimentaire',
                'website': 'https://www.cosumar.sn',
                'email': 'recrutement@cosumar.sn'
            },
            {
                'company_name': 'Banque de l\'Habitat du Sénégal',
                'sector': 'Banque et Assurance',
                'website': 'https://www.bhs.sn',
                'email': 'recrutement@bhs.sn'
            },
            {
                'company_name': 'Campusen',
                'sector': 'Éducation et Formation',
                'website': 'https://www.campusen.sn',
                'email': 'recrutement@campusen.sn'
            },
            {
                'company_name': 'Jokkolabs',
                'sector': 'Innovation et Technologie',
                'website': 'https://www.jokkolabs.net',
                'email': 'contact@jokkolabs.net'
            }
        ]
        
        for i, ent_data in enumerate(enterprises_data):
            ent_user, created = User.objects.get_or_create(
                email=ent_data['email'],
                defaults={
                    'username': f"entreprise_{ent_data['company_name'].lower().replace(' ', '_')}",
                    'first_name': ent_data['company_name'],
                    'last_name': 'Recrutement',
                    'role': 'enterprise',
                    'is_active': True
                }
            )
            if created:
                ent_user.set_password('entreprise123')
                ent_user.save()
                Enterprise.objects.create(
                    user=ent_user,
                    company_name=ent_data['company_name'],
                    sector=ent_data['sector'],
                    website=ent_data['website']
                )
                users['enterprises'].append(ent_user)
        
        # Créer des étudiants
        students_data = [
            {'first_name': 'Amadou', 'last_name': 'Diallo', 'gender': 'M', 'institution': 0},
            {'first_name': 'Fatou', 'last_name': 'Ndiaye', 'gender': 'F', 'institution': 0},
            {'first_name': 'Moussa', 'last_name': 'Sow', 'gender': 'M', 'institution': 1},
            {'first_name': 'Aïssatou', 'last_name': 'Ba', 'gender': 'F', 'institution': 1},
            {'first_name': 'Ibrahima', 'last_name': 'Sy', 'gender': 'M', 'institution': 2},
            {'first_name': 'Mariama', 'last_name': 'Diop', 'gender': 'F', 'institution': 2},
            {'first_name': 'Ousmane', 'last_name': 'Fall', 'gender': 'M', 'institution': 3},
            {'first_name': 'Khady', 'last_name': 'Seck', 'gender': 'F', 'institution': 3},
            {'first_name': 'Abdoulaye', 'last_name': 'Mbaye', 'gender': 'M', 'institution': 4},
            {'first_name': 'Awa', 'last_name': 'Gueye', 'gender': 'F', 'institution': 4},
            {'first_name': 'Cheikh', 'last_name': 'Thiam', 'gender': 'M', 'institution': 5},
            {'first_name': 'Sokhna', 'last_name': 'Cissé', 'gender': 'F', 'institution': 5},
            {'first_name': 'Mamadou', 'last_name': 'Kane', 'gender': 'M', 'institution': 6},
            {'first_name': 'Rama', 'last_name': 'Sarr', 'gender': 'F', 'institution': 6},
            {'first_name': 'Lamine', 'last_name': 'Touré', 'gender': 'M', 'institution': 7},
            {'first_name': 'Ndèye', 'last_name': 'Faye', 'gender': 'F', 'institution': 7},
        ]
        
        for i, student_data in enumerate(students_data):
            email = f"{student_data['first_name'].lower()}.{student_data['last_name'].lower()}@etudiant.sn"
            student_user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': f"student_{i+1}",
                    'first_name': student_data['first_name'],
                    'last_name': student_data['last_name'],
                    'role': 'student',
                    'is_active': True
                }
            )
            if created:
                student_user.set_password('etudiant123')
                student_user.save()
                
                # Créer le profil étudiant
                student = Student.objects.create(
                    user=student_user,
                    gender=student_data['gender'],
                    date_of_birth=date(1998 + random.randint(0, 5), random.randint(1, 12), random.randint(1, 28)),
                    student_id=f"ETU{2020 + i:04d}{i+1:03d}"
                )
                
                # Ajouter l'étudiant à l'institution
                if student_data['institution'] < len(institutions):
                    from apps.api.v1.establishments.models import StudentInstitution
                    StudentInstitution.objects.create(
                        student=student,
                        institution=institutions[student_data['institution']],
                        is_primary=True
                    )
                
                users['students'].append(student_user)
        
        # Créer des alumni
        alumni_data = [
            {'first_name': 'Ibou', 'last_name': 'Diack', 'gender': 'M', 'institution': 0, 'graduation_year': 2020},
            {'first_name': 'Amina', 'last_name': 'Sylla', 'gender': 'F', 'institution': 0, 'graduation_year': 2019},
            {'first_name': 'Pape', 'last_name': 'Diouf', 'gender': 'M', 'institution': 1, 'graduation_year': 2021},
            {'first_name': 'Coumba', 'last_name': 'Diallo', 'gender': 'F', 'institution': 2, 'graduation_year': 2018},
            {'first_name': 'Samba', 'last_name': 'Ndiaye', 'gender': 'M', 'institution': 3, 'graduation_year': 2020},
            {'first_name': 'Yacine', 'last_name': 'Ba', 'gender': 'F', 'institution': 4, 'graduation_year': 2019},
        ]
        
        for i, alumni_data in enumerate(alumni_data):
            email = f"{alumni_data['first_name'].lower()}.{alumni_data['last_name'].lower()}@alumni.sn"
            alumni_user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': f"alumni_{i+1}",
                    'first_name': alumni_data['first_name'],
                    'last_name': alumni_data['last_name'],
                    'role': 'alumni',
                    'is_active': True
                }
            )
            if created:
                alumni_user.set_password('alumni123')
                alumni_user.save()
                
                # Créer le profil alumni
                alumni = Alumni.objects.create(
                    user=alumni_user,
                    gender=alumni_data['gender'],
                    graduation_date=date(alumni_data['graduation_year'], 6, 30),
                    institution=institutions[alumni_data['institution']]
                )
                
                users['alumni'].append(alumni_user)
        
        self.stdout.write(self.style.SUCCESS(f'  - {len(users["students"])} étudiants'))
        self.stdout.write(self.style.SUCCESS(f'  - {len(users["alumni"])} alumni'))
        self.stdout.write(self.style.SUCCESS(f'  - {len(users["enterprises"])} entreprises'))
        self.stdout.write(self.style.SUCCESS(f'  - {len(users["admins"])} admins'))
        
        return users

    def create_posts(self, users, institutions):
        """Créer des posts, opportunités et événements"""
        self.stdout.write('Création des posts et opportunités...')
        
        # Opportunités d'emploi
        opportunities_data = [
            {
                'title': 'Développeur Web Junior - Sonatel',
                'content': 'Sonatel recrute un développeur web junior pour rejoindre son équipe IT. Missions : développement et maintenance des applications web, participation aux projets digitaux.',
                'category': 'job',
                'contract_type': 'permanent',
                'work_mode': 'hybrid',
                'location_city': 'Dakar',
                'location_country': 'Sénégal',
                'salary_min': 800000,
                'salary_max': 1200000,
                'currency': 'XOF',
                'enterprise': 0,
                'required_skills': ['Développement Web', 'JavaScript', 'Python']
            },
            {
                'title': 'Stage Marketing Digital - Jokkolabs',
                'content': 'Jokkolabs offre un stage de 6 mois en marketing digital. Le stagiaire participera à la stratégie de communication digitale et à la gestion des réseaux sociaux.',
                'category': 'internship',
                'work_mode': 'onsite',
                'location_city': 'Dakar',
                'location_country': 'Sénégal',
                'duration_months': 6,
                'enterprise': 5,
                'required_skills': ['Marketing digital', 'Communication', 'Réseaux sociaux']
            },
            {
                'title': 'Ingénieur Data - Banque de l\'Habitat',
                'content': 'La BHS recrute un ingénieur data pour son département informatique. Missions : analyse de données, création de tableaux de bord, optimisation des processus.',
                'category': 'job',
                'contract_type': 'permanent',
                'work_mode': 'onsite',
                'location_city': 'Dakar',
                'location_country': 'Sénégal',
                'salary_min': 1500000,
                'salary_max': 2500000,
                'currency': 'XOF',
                'enterprise': 3,
                'required_skills': ['Analyse de données', 'Python', 'SQL', 'Machine Learning']
            },
            {
                'title': 'Formation en Développement Mobile - Campusen',
                'content': 'Campusen propose une formation intensive de 3 mois en développement mobile Android et iOS. Certification à la clé.',
                'category': 'training',
                'work_mode': 'hybrid',
                'location_city': 'Dakar',
                'location_country': 'Sénégal',
                'duration_months': 3,
                'enterprise': 4,
                'required_skills': ['Développement Mobile', 'Android', 'iOS']
            },
            {
                'title': 'Assistant Comptable - Cosumar',
                'content': 'Cosumar recrute un assistant comptable pour renforcer son équipe finance. Missions : saisie comptable, rapprochements bancaires, reporting.',
                'category': 'job',
                'contract_type': 'fixed_term',
                'work_mode': 'onsite',
                'location_city': 'Dakar',
                'location_country': 'Sénégal',
                'salary_min': 600000,
                'salary_max': 900000,
                'currency': 'XOF',
                'enterprise': 2,
                'required_skills': ['Comptabilité', 'Finance', 'Excel']
            },
            {
                'title': 'Bénévolat - Association Jappo',
                'content': 'L\'association Jappol recherche des bénévoles pour accompagner les étudiants dans leur insertion professionnelle. Mentorat, ateliers CV, simulations d\'entretiens.',
                'category': 'volunteer',
                'work_mode': 'hybrid',
                'location_city': 'Dakar',
                'location_country': 'Sénégal',
                'required_skills': ['Mentorat', 'Communication', 'Service client']
            }
        ]
        
        for i, opp_data in enumerate(opportunities_data):
            # Créer le post
            post = Post.objects.create(
                author=users['enterprises'][opp_data['enterprise']],
                title=opp_data['title'],
                content=opp_data['content'],
                post_type='opportunity',
                audience='public',
                institution=institutions[0] if i % 2 == 0 else None
            )
            
            # Créer l'opportunité
            Opportunity.objects.create(
                post=post,
                enterprise=users['enterprises'][opp_data['enterprise']].enterprise_profile,
                category=opp_data['category'],
                contract_type=opp_data.get('contract_type', ''),
                work_mode=opp_data['work_mode'],
                location_city=opp_data['location_city'],
                location_country=opp_data['location_country'],
                salary_min=opp_data.get('salary_min'),
                salary_max=opp_data.get('salary_max'),
                currency=opp_data.get('currency', 'XOF'),
                duration_months=opp_data.get('duration_months'),
                required_skills=opp_data.get('required_skills', []),
                status='open'
            )
        
        # Événements
        events_data = [
            {
                'title': 'Forum de l\'Emploi UCAD 2024',
                'content': 'Le traditionnel forum de l\'emploi de l\'UCAD revient avec plus de 50 entreprises exposantes. Venez à la rencontre de recruteurs et découvrez les opportunités disponibles.',
                'starts_at': timezone.now() + timedelta(days=30),
                'ends_at': timezone.now() + timedelta(days=30, hours=8),
                'location_name': 'Campus UCAD',
                'address': 'Avenue Cheikh Anta Diop',
                'city': 'Dakar',
                'country': 'Sénégal',
                'capacity': 2000,
                'author': 0  # admin
            },
            {
                'title': 'Hackathon Innovation Digitale',
                'content': '48h pour développer des solutions innovantes aux défis locaux. Prix attractifs et opportunités de stage pour les gagnants.',
                'starts_at': timezone.now() + timedelta(days=45),
                'ends_at': timezone.now() + timedelta(days=47),
                'location_name': 'Jokkolabs',
                'address': 'Rue de Thann',
                'city': 'Dakar',
                'country': 'Sénégal',
                'capacity': 100,
                'author': 5  # Jokkolabs
            },
            {
                'title': 'Conférence sur l\'Entrepreneuriat',
                'content': 'Rencontrez des entrepreneurs à succès et apprenez de leurs expériances. Panel, networking et sessions de mentorat.',
                'starts_at': timezone.now() + timedelta(days=15),
                'ends_at': timezone.now() + timedelta(days=15, hours=4),
                'location_name': 'Hôtel Terrou-Bi',
                'address': 'Boulevard Martin Luther King',
                'city': 'Dakar',
                'country': 'Sénégal',
                'capacity': 300,
                'author': 4  # Campusen
            }
        ]
        
        for i, event_data in enumerate(events_data):
            post = Post.objects.create(
                author=users['admins'][event_data['author']] if event_data['author'] < len(users['admins']) else users['enterprises'][0],
                title=event_data['title'],
                content=event_data['content'],
                post_type='event',
                audience='public'
            )
            
            Event.objects.create(
                post=post,
                starts_at=event_data['starts_at'],
                ends_at=event_data['ends_at'],
                location_name=event_data['location_name'],
                address=event_data['address'],
                city=event_data['city'],
                country=event_data['country'],
                capacity=event_data['capacity']
            )
        
        # Posts de discussion
        discussions_data = [
            {
                'title': 'Conseils pour réussir son stage',
                'content': 'Bonjour à tous! Je commence mon stage chez Sonatel le mois prochain. Avez-vous des conseils pour bien débuter et faire bonne impression?',
                'author': 0,  # premier étudiant
                'audience': 'general_promotion'
            },
            {
                'title': 'Recherche de coéquipiers pour projet IoT',
                'content': 'Je cherche 2-3 personnes pour monter un projet de capteurs IoT pour l\'agriculture. Idéalement avec des compétences en électronique et développement embarqué.',
                'author': 4,  # étudiant
                'audience': 'public'
            },
            {
                'title': 'Partage d\'expérience - Entretien chez Sénélec',
                'content': 'Je viens de passer un entretien chez Sénélec. Voici mon retour d\'expérience pour ceux qui postulent...',
                'author': 8,  # étudiant
                'audience': 'public'
            }
        ]
        
        for disc_data in discussions_data:
            Post.objects.create(
                author=users['students'][disc_data['author']],
                title=disc_data['title'],
                content=disc_data['content'],
                post_type='discussion',
                audience=disc_data['audience'],
                institution=institutions[0] if disc_data['audience'] == 'general_promotion' else None
            )
        
        self.stdout.write(self.style.SUCCESS(f'  - {Opportunity.objects.count()} opportunités'))
        self.stdout.write(self.style.SUCCESS(f'  - {Event.objects.count()} événements'))
        self.stdout.write(self.style.SUCCESS(f'  - {Post.objects.filter(post_type="discussion").count()} discussions'))

    def create_conversations(self, users):
        """Créer des conversations et messages"""
        self.stdout.write('Création des conversations...')
        
        # Conversations directes
        direct_conversations = [
            (0, 0),  # étudiant 1 et admin 1
            (1, 1),  # étudiant 2 et admin 2
            (4, 0),  # étudiant 5 et admin 1
        ]
        
        for student_idx, admin_idx in direct_conversations:
            if student_idx < len(users['students']) and admin_idx < len(users['admins']):
                conv = Conversation.objects.create(
                    conversation_type='direct',
                    created_by=users['students'][student_idx]
                )
                
                ConversationParticipant.objects.create(
                    conversation=conv,
                    user=users['students'][student_idx],
                    role='member'
                )
                
                ConversationParticipant.objects.create(
                    conversation=conv,
                    user=users['admins'][admin_idx],
                    role='member'
                )
                
                # Ajouter quelques messages
                messages = [
                    'Bonjour, j\'ai une question concernant mon inscription.',
                    'Bien sûr, je suis à votre disposition. Quelle est votre question?',
                    'Je voudrais savoir comment obtenir mon certificat de scolarité.',
                    'Vous pouvez le demander via le portail étudiant ou passer au service de la scolarité.'
                ]
                
                for i, msg_content in enumerate(messages):
                    Message.objects.create(
                        conversation=conv,
                        sender=users['students'][student_idx] if i % 2 == 0 else users['admins'][admin_idx],
                        content=msg_content,
                        message_type='text'
                    )
        
        # Groupe de promotion
        if users['students']:
            group_conv = Conversation.objects.create(
                conversation_type='group',
                name='Promotion Générale UCAD 2024',
                description='Groupe de discussion pour tous les étudiants de l\'UCAD',
                created_by=users['admins'][0] if users['admins'] else users['students'][0]
            )
            
            # Ajouter les participants
            for student_user in users['students'][:5]:
                ConversationParticipant.objects.create(
                    conversation=group_conv,
                    user=student_user,
                    role='member'
                )
            
            if users['admins']:
                ConversationParticipant.objects.create(
                    conversation=group_conv,
                    user=users['admins'][0],
                    role='admin'
                )
            
            # Messages dans le groupe
            group_messages = [
                'Bienvenue dans le groupe de la promotion!',
                'Merci pour l\'initiative!',
                'Est-ce que quelqu\'un a des informations sur le prochain examen?',
                'L\'examen de programmation est prévu le 15 du mois prochain.',
                'Merci pour l\'info!'
            ]
            
            for i, msg_content in enumerate(group_messages):
                Message.objects.create(
                    conversation=group_conv,
                    sender=users['students'][i % len(users['students'])],
                    content=msg_content,
                    message_type='text'
                )
        
        self.stdout.write(self.style.SUCCESS(f'  - {Conversation.objects.count()} conversations'))
        self.stdout.write(self.style.SUCCESS(f'  - {Message.objects.count()} messages'))
