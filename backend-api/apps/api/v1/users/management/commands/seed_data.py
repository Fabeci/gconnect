"""
Commande de peuplement de la base de données avec des données de test réalistes.
Usage : python manage.py seed_data
"""
import random
from datetime import date, timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import transaction
from rest_framework.authtoken.models import Token

from apps.api.v1.core.models import Skill, Interest, Preference, Sector
from apps.api.v1.users.models import User, Student, Alumni, InstitutionAdmin, Enterprise
from apps.api.v1.establishments.models import (
    Institution, Promotion, StudentInstitution, AlumniInstitution,
    PromotionMembership, AlumniPromotionMembership, StudentAccountOrder,
)
from apps.api.v1.posts.models import (
    Post, Opportunity, Event, Project, Comment, Reaction, Application, RSVP, Bookmark,
)
from apps.api.v1.messaging.models import Conversation, ConversationParticipant, Message

PASSWORD = "Test@1234"


# ---------------------------------------------------------------------------
# Données de référence
# ---------------------------------------------------------------------------

SKILLS_DATA = [
    "Python", "Django", "JavaScript", "React", "Flutter", "Dart",
    "SQL", "PostgreSQL", "Docker", "Git", "Machine Learning", "Data Science",
    "Java", "Spring Boot", "Node.js", "TypeScript", "DevOps", "Linux",
    "Marketing Digital", "Gestion de projet", "Communication", "Leadership",
]

INTERESTS_DATA = [
    "Intelligence Artificielle", "Développement Web", "Mobile",
    "Entrepreneuriat", "Finance", "Santé", "Education", "Sport",
    "Arts & Culture", "Environnement", "Innovation", "Recherche",
]

PREFERENCES_DATA = [
    "Travail en équipe", "Télétravail", "Startup", "Grande entreprise",
    "ONG", "Secteur public", "Freelance", "Mentorat",
]

SECTORS_DATA = [
    "Technologie", "Finance & Banque", "Santé", "Education",
    "Agriculture", "Commerce", "Energie", "Telecoms",
    "Administration publique", "Media & Communication",
]

INSTITUTIONS_DATA = [
    {
        "name": "Université Cheikh Anta Diop",
        "acronym": "UCAD",
        "address": "Dakar, Sénégal",
        "email": "contact@ucad.sn",
        "website": "https://www.ucad.sn",
        "established_year": 1957,
        "description": "La plus grande université d'Afrique de l'Ouest francophone.",
    },
    {
        "name": "École Supérieure Polytechnique",
        "acronym": "ESP",
        "address": "Dakar, Sénégal",
        "email": "contact@esp.sn",
        "website": "https://www.esp.sn",
        "established_year": 1994,
        "description": "École d'ingénieurs de référence au Sénégal.",
    },
    {
        "name": "Institut Supérieur de Management",
        "acronym": "ISM",
        "address": "Dakar, Sénégal",
        "email": "contact@ism.sn",
        "website": "https://www.ism.sn",
        "established_year": 1992,
        "description": "Premier MBA d'Afrique subsaharienne francophone.",
    },
]

PROMOTIONS_DATA = [
    {"name": "L3 Informatique 2024", "year": 2024, "department": "Informatique", "level": "L3"},
    {"name": "M1 Génie Logiciel 2024", "year": 2024, "department": "Génie Logiciel", "level": "M1"},
    {"name": "M2 Réseaux & Télécom 2024", "year": 2024, "department": "Réseaux", "level": "M2"},
    {"name": "L2 Mathématiques 2024", "year": 2024, "department": "Mathématiques", "level": "L2"},
    {"name": "M1 Finance 2024", "year": 2024, "department": "Finance", "level": "M1"},
]

STUDENTS_DATA = [
    {"username": "amadou_diallo", "first_name": "Amadou", "last_name": "Diallo",
     "email": "amadou.diallo@students.test", "gender": "M", "dob": date(2001, 3, 15)},
    {"username": "fatou_sall", "first_name": "Fatou", "last_name": "Sall",
     "email": "fatou.sall@students.test", "gender": "F", "dob": date(2000, 7, 22)},
    {"username": "moussa_ba", "first_name": "Moussa", "last_name": "Ba",
     "email": "moussa.ba@students.test", "gender": "M", "dob": date(2002, 1, 10)},
    {"username": "aissatou_ndiaye", "first_name": "Aissatou", "last_name": "Ndiaye",
     "email": "aissatou.ndiaye@students.test", "gender": "F", "dob": date(2001, 11, 5)},
    {"username": "oumar_fall", "first_name": "Oumar", "last_name": "Fall",
     "email": "oumar.fall@students.test", "gender": "M", "dob": date(2003, 6, 18)},
    {"username": "mariama_sy", "first_name": "Mariama", "last_name": "Sy",
     "email": "mariama.sy@students.test", "gender": "F", "dob": date(2000, 9, 30)},
]

ALUMNI_DATA = [
    {"username": "ibrahima_diop", "first_name": "Ibrahima", "last_name": "Diop",
     "email": "ibrahima.diop@alumni.test", "gender": "M", "grad": date(2020, 6, 30)},
    {"username": "rokhaya_cisse", "first_name": "Rokhaya", "last_name": "Cisse",
     "email": "rokhaya.cisse@alumni.test", "gender": "F", "grad": date(2021, 7, 15)},
    {"username": "pape_ngom", "first_name": "Pape", "last_name": "Ngom",
     "email": "pape.ngom@alumni.test", "gender": "M", "grad": date(2019, 6, 30)},
]

ENTERPRISES_DATA = [
    {"username": "sonatel_rh", "first_name": "Sonatel", "last_name": "RH",
     "email": "rh@sonatel.test", "company": "Sonatel", "sector": "Telecoms"},
    {"username": "orange_sn", "first_name": "Orange", "last_name": "Sénégal",
     "email": "career@orange.test", "company": "Orange Sénégal", "sector": "Telecoms"},
    {"username": "wave_africa", "first_name": "Wave", "last_name": "Africa",
     "email": "jobs@wave.test", "company": "Wave Africa", "sector": "Fintech"},
]

INSTITUTION_ADMINS_DATA = [
    {"username": "admin_ucad", "first_name": "Admin", "last_name": "UCAD",
     "email": "admin@ucad.test"},
    {"username": "admin_esp", "first_name": "Admin", "last_name": "ESP",
     "email": "admin@esp.test"},
    {"username": "admin_ism", "first_name": "Admin", "last_name": "ISM",
     "email": "admin@ism.test"},
]


class Command(BaseCommand):
    help = "Peuple la base de données avec des données de test réalistes"

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Peuplement de la base de donnees ===\n"))

        with transaction.atomic():
            skills, interests = self._seed_core()
            institutions = self._seed_institutions()
            promotions = self._seed_promotions(institutions)
            admins = self._seed_institution_admins(institutions)
            students = self._seed_students(institutions, promotions, skills, interests)
            alumni = self._seed_alumni(institutions, promotions, skills, interests)
            enterprises = self._seed_enterprises()
            all_users = admins + [s["user"] for s in students] + [a["user"] for a in alumni] + enterprises
            posts = self._seed_posts(all_users, institutions, promotions, enterprises)
            self._seed_interactions(posts, all_users, students, enterprises)
            self._seed_messages(all_users)

        self.stdout.write(self.style.SUCCESS("\n=== Peuplement termine avec succes ==="))
        self.stdout.write(f"Mot de passe de tous les comptes : {PASSWORD}\n")

    # ------------------------------------------------------------------
    # Core (Skills, Interests, Preferences, Sectors)
    # ------------------------------------------------------------------

    def _seed_core(self):
        for name in SKILLS_DATA:
            Skill.objects.get_or_create(name=name)
        for name in INTERESTS_DATA:
            Interest.objects.get_or_create(name=name)
        for name in PREFERENCES_DATA:
            Preference.objects.get_or_create(name=name)
        for name in SECTORS_DATA:
            Sector.objects.get_or_create(name=name)

        skills = list(Skill.objects.all())
        interests = list(Interest.objects.all())
        self.stdout.write(self.style.SUCCESS(
            f"  [+] Core : {len(skills)} skills, {len(interests)} interests"
        ))
        return skills, interests

    # ------------------------------------------------------------------
    # Institutions
    # ------------------------------------------------------------------

    def _seed_institutions(self):
        institutions = []
        for data in INSTITUTIONS_DATA:
            inst, created = Institution.objects.get_or_create(
                name=data["name"],
                defaults={
                    "acronym": data["acronym"],
                    "address": data["address"],
                    "email": data["email"],
                    "website": data["website"],
                    "established_year": data["established_year"],
                    "description": data["description"],
                    "is_active": True,
                },
            )
            institutions.append(inst)
            tag = "[+]" if created else "[=]"
            self.stdout.write(f"  {tag} Institution : {inst.name}")
        return institutions

    # ------------------------------------------------------------------
    # Promotions spécifiques (la générale est auto-créée par Institution.save())
    # ------------------------------------------------------------------

    def _seed_promotions(self, institutions):
        promotions = []
        for i, promo_data in enumerate(PROMOTIONS_DATA):
            institution = institutions[i % len(institutions)]
            promo, created = Promotion.objects.get_or_create(
                name=promo_data["name"],
                institution=institution,
                defaults={
                    "year": promo_data["year"],
                    "department": promo_data["department"],
                    "level": promo_data["level"],
                    "is_general": False,
                },
            )
            promotions.append(promo)
        self.stdout.write(self.style.SUCCESS(f"  [+] Promotions specifiques : {len(promotions)}"))
        return promotions

    # ------------------------------------------------------------------
    # Admins établissement
    # ------------------------------------------------------------------

    def _seed_institution_admins(self, institutions):
        admins = []
        for i, data in enumerate(INSTITUTION_ADMINS_DATA):
            institution = institutions[i % len(institutions)]
            user = self._create_user(data, "etablissement", is_staff=True)
            if user:
                InstitutionAdmin.objects.get_or_create(
                    user=user, defaults={"institution": institution}
                )
            admins.append(user)
            self.stdout.write(f"  [+] Admin etab : {data['email']} -> {institution.acronym}")
        return [u for u in admins if u]

    # ------------------------------------------------------------------
    # Étudiants
    # ------------------------------------------------------------------

    def _seed_students(self, institutions, promotions, skills, interests):
        results = []
        for i, data in enumerate(STUDENTS_DATA):
            user = self._create_user(
                {"username": data["username"], "first_name": data["first_name"],
                 "last_name": data["last_name"], "email": data["email"]},
                "student"
            )
            if not user:
                continue

            student, _ = Student.objects.get_or_create(
                user=user,
                defaults={
                    "gender": data["gender"],
                    "date_of_birth": data["dob"],
                    "student_id": f"STU{i+100:04d}",
                },
            )

            # Assigner des compétences et intérêts aléatoires
            if skills:
                student.skills.set(random.sample(skills, min(4, len(skills))))
            if interests:
                student.interests.set(random.sample(interests, min(3, len(interests))))

            # Rattacher à 1-2 établissements
            institution = institutions[i % len(institutions)]
            StudentInstitution.objects.get_or_create(student=student, institution=institution)

            # Rattacher à une promotion spécifique
            if promotions:
                promo = promotions[i % len(promotions)]
                if promo.institution == institution:
                    PromotionMembership.objects.get_or_create(
                        student=student,
                        promotion=promo,
                        defaults={"is_approved": True},
                    )

            results.append({"user": user, "student": student})
            self.stdout.write(f"  [+] Etudiant : {data['email']}")
        return results

    # ------------------------------------------------------------------
    # Alumni
    # ------------------------------------------------------------------

    def _seed_alumni(self, institutions, promotions, skills, interests):
        results = []
        for i, data in enumerate(ALUMNI_DATA):
            user = self._create_user(
                {"username": data["username"], "first_name": data["first_name"],
                 "last_name": data["last_name"], "email": data["email"]},
                "alumni"
            )
            if not user:
                continue

            institution = institutions[i % len(institutions)]
            alumni_obj, _ = Alumni.objects.get_or_create(
                user=user,
                defaults={
                    "gender": data["gender"],
                    "graduation_date": data["grad"],
                    "institution": institution,
                    "proof_document": "",
                },
            )

            if skills:
                alumni_obj.skills.set(random.sample(skills, min(5, len(skills))))
            if interests:
                alumni_obj.interests.set(random.sample(interests, min(3, len(interests))))

            AlumniInstitution.objects.get_or_create(alumni=alumni_obj, institution=institution)

            results.append({"user": user, "alumni": alumni_obj})
            self.stdout.write(f"  [+] Alumni : {data['email']}")
        return results

    # ------------------------------------------------------------------
    # Entreprises
    # ------------------------------------------------------------------

    def _seed_enterprises(self):
        enterprise_users = []
        for data in ENTERPRISES_DATA:
            user = self._create_user(
                {"username": data["username"], "first_name": data["first_name"],
                 "last_name": data["last_name"], "email": data["email"]},
                "enterprise"
            )
            if not user:
                enterprise_users.append(user)
                continue

            Enterprise.objects.get_or_create(
                user=user,
                defaults={"company_name": data["company"], "sector": data["sector"]},
            )
            enterprise_users.append(user)
            self.stdout.write(f"  [+] Entreprise : {data['email']}")
        return [u for u in enterprise_users if u]

    # ------------------------------------------------------------------
    # Posts
    # ------------------------------------------------------------------

    def _seed_posts(self, all_users, institutions, promotions, enterprise_users):
        posts = []

        # --- Discussions ---
        discussions = [
            ("Bienvenue sur G-Connect !", "Heureux de rejoindre cette plateforme. Qui veut se connecter ?"),
            ("Conseils pour les stages en tech", "Quels conseils donneriez-vous a un etudiant qui cherche un stage dans la tech ?"),
            ("Retour d'experience : alternance chez Orange", "J'ai fait mon alternance chez Orange Senegal pendant 1 an. Voici ce que j'ai appris..."),
            ("Ressources pour apprendre Django", "Je partage une liste de ressources pour apprendre Django REST Framework."),
            ("Networking : comment developper son reseau ?", "En tant qu'etudiants, le reseau est essentiel. Partage tes strategies !"),
        ]
        for i, (title, content) in enumerate(discussions):
            author = all_users[i % len(all_users)]
            post, created = Post.objects.get_or_create(
                title=title,
                author=author,
                defaults={
                    "content": content,
                    "post_type": Post.PostType.DISCUSSION,
                    "audience": Post.Audience.PUBLIC,
                    "institution": institutions[i % len(institutions)] if i % 2 == 0 else None,
                },
            )
            posts.append(post)

        # --- Opportunités ---
        if enterprise_users:
            opps = [
                {
                    "title": "Stage Developpeur Flutter - Wave Africa",
                    "content": "Nous recherchons un stagiaire Flutter passionne pour rejoindre notre equipe produit.",
                    "category": Opportunity.Category.INTERNSHIP,
                    "location_city": "Dakar",
                    "location_country": "Senegal",
                    "work_mode": Opportunity.WorkMode.ONSITE,
                    "duration_months": 6,
                    "deadline": date.today() + timedelta(days=30),
                    "tags": ["Flutter", "Dart", "Mobile"],
                },
                {
                    "title": "Ingenieur Backend Python - Sonatel",
                    "content": "CDI - Rejoignez l'equipe engineering de Sonatel pour construire des APIs scalables.",
                    "category": Opportunity.Category.JOB,
                    "location_city": "Dakar",
                    "location_country": "Senegal",
                    "work_mode": Opportunity.WorkMode.HYBRID,
                    "contract_type": Opportunity.ContractType.PERMANENT,
                    "salary_min": 600000,
                    "salary_max": 900000,
                    "currency": "XOF",
                    "deadline": date.today() + timedelta(days=45),
                    "tags": ["Python", "Django", "PostgreSQL"],
                },
                {
                    "title": "Alternance Data Science - Orange Senegal",
                    "content": "Alternance de 12 mois au sein de notre departement Data & IA.",
                    "category": Opportunity.Category.APPRENTICESHIP,
                    "location_city": "Dakar",
                    "location_country": "Senegal",
                    "work_mode": Opportunity.WorkMode.HYBRID,
                    "duration_months": 12,
                    "deadline": date.today() + timedelta(days=20),
                    "tags": ["Python", "Machine Learning", "Data Science"],
                },
            ]
            for i, opp_data in enumerate(opps):
                author = enterprise_users[i % len(enterprise_users)]
                post, created = Post.objects.get_or_create(
                    title=opp_data["title"],
                    author=author,
                    defaults={
                        "content": opp_data["content"],
                        "post_type": Post.PostType.OPPORTUNITY,
                        "audience": Post.Audience.PUBLIC,
                    },
                )
                if created:
                    opp_kwargs = {
                        "post": post,
                        "category": opp_data["category"],
                        "location_city": opp_data.get("location_city", ""),
                        "location_country": opp_data.get("location_country", ""),
                        "work_mode": opp_data.get("work_mode", Opportunity.WorkMode.ONSITE),
                        "status": Opportunity.Status.OPEN,
                        "deadline": opp_data.get("deadline"),
                        "tags": opp_data.get("tags", []),
                        "duration_months": opp_data.get("duration_months"),
                        "contract_type": opp_data.get("contract_type", ""),
                        "salary_min": opp_data.get("salary_min"),
                        "salary_max": opp_data.get("salary_max"),
                        "currency": opp_data.get("currency", "XOF"),
                    }
                    Opportunity.objects.create(**opp_kwargs)
                posts.append(post)

        # --- Événements ---
        events_data = [
            {
                "title": "Forum de l'emploi UCAD 2024",
                "content": "Rencontrez plus de 50 entreprises partenaires et decrochez votre prochain emploi ou stage.",
                "starts_at": timezone.now() + timedelta(days=15),
                "ends_at": timezone.now() + timedelta(days=15, hours=8),
                "location_name": "Salle de conference UCAD",
                "city": "Dakar",
                "is_online": False,
                "capacity": 500,
            },
            {
                "title": "Webinaire : Carriere dans la Fintech",
                "content": "Comment lancer sa carriere dans la Fintech en Afrique ? Conseils d'experts.",
                "starts_at": timezone.now() + timedelta(days=7),
                "ends_at": timezone.now() + timedelta(days=7, hours=2),
                "is_online": True,
                "online_url": "https://meet.google.com/test-event",
                "capacity": 200,
            },
        ]
        for i, ev_data in enumerate(events_data):
            author = all_users[i % len(all_users)]
            post, created = Post.objects.get_or_create(
                title=ev_data["title"],
                author=author,
                defaults={
                    "content": ev_data["content"],
                    "post_type": Post.PostType.EVENT,
                    "audience": Post.Audience.PUBLIC,
                },
            )
            if created:
                Event.objects.create(
                    post=post,
                    starts_at=ev_data["starts_at"],
                    ends_at=ev_data.get("ends_at"),
                    is_online=ev_data.get("is_online", False),
                    location_name=ev_data.get("location_name", ""),
                    city=ev_data.get("city", ""),
                    online_url=ev_data.get("online_url", ""),
                    capacity=ev_data.get("capacity"),
                )
            posts.append(post)

        # --- Projets ---
        projects_data = [
            {
                "title": "Application de covoiturage pour etudiants",
                "content": "Je developpe une app Flutter de covoiturage pour les etudiants de Dakar. Cherche co-developpeurs !",
                "required_skills": ["Flutter", "Firebase", "Google Maps"],
            },
            {
                "title": "Plateforme de tutorat en ligne",
                "content": "Projet de plateforme mettant en relation etudiants avances et debutants pour du tutorat.",
                "required_skills": ["Django", "React", "PostgreSQL"],
            },
        ]
        for i, proj_data in enumerate(projects_data):
            author = all_users[i % len(all_users)]
            post, created = Post.objects.get_or_create(
                title=proj_data["title"],
                author=author,
                defaults={
                    "content": proj_data["content"],
                    "post_type": Post.PostType.PROJECT,
                    "audience": Post.Audience.PUBLIC,
                },
            )
            if created:
                Project.objects.create(
                    post=post,
                    status=Project.Status.ACTIVE,
                    looking_for_members=True,
                    required_skills=proj_data["required_skills"],
                )
            posts.append(post)

        self.stdout.write(self.style.SUCCESS(f"  [+] Posts : {len(posts)} crees"))
        return posts

    # ------------------------------------------------------------------
    # Interactions (commentaires, reactions, candidatures, RSVP, bookmarks)
    # ------------------------------------------------------------------

    def _seed_interactions(self, posts, all_users, students, enterprise_users):
        comments_texts = [
            "Super initiative, merci pour le partage !",
            "Tres interessant. J'ai une question : quelles sont les conditions ?",
            "Je suis interesse, comment postuler ?",
            "Merci pour cette opportunite !",
            "Excellent contenu, continuez comme ca.",
            "Quelqu'un a deja postule ? Des retours ?",
            "Ce type de poste correspond exactement a mon profil.",
        ]

        reaction_kinds = list(Reaction.Kind.values)

        for i, post in enumerate(posts):
            # Commentaires (2-4 par post)
            commenters = random.sample(all_users, min(3, len(all_users)))
            for j, user in enumerate(commenters):
                Comment.objects.get_or_create(
                    user=user,
                    post=post,
                    content=comments_texts[(i + j) % len(comments_texts)],
                )

            # Réactions (3-6 par post)
            reactors = random.sample(all_users, min(5, len(all_users)))
            for user in reactors:
                Reaction.objects.get_or_create(
                    user=user,
                    post=post,
                    defaults={"kind": random.choice(reaction_kinds)},
                )

            # Bookmarks (sur quelques posts)
            if i % 2 == 0 and all_users:
                bm_user = all_users[i % len(all_users)]
                Bookmark.objects.get_or_create(user=bm_user, post=post)

        # Candidatures : étudiants -> opportunités
        opportunity_posts = [p for p in posts if p.post_type == Post.PostType.OPPORTUNITY]
        for opp_post in opportunity_posts:
            if not hasattr(opp_post, 'opportunity'):
                continue
            opp = opp_post.opportunity
            applicants = random.sample(students, min(3, len(students)))
            for item in applicants:
                user = item["user"]
                Application.objects.get_or_create(
                    user=user,
                    opportunity=opp,
                    defaults={
                        "cover_letter": f"Je suis tres motive pour rejoindre votre equipe. Mon profil correspond a vos attentes.",
                        "status": random.choice(["submitted", "viewed", "shortlisted"]),
                    },
                )

        # RSVPs : utilisateurs -> événements
        event_posts = [p for p in posts if p.post_type == Post.PostType.EVENT]
        for ev_post in event_posts:
            if not hasattr(ev_post, 'event'):
                continue
            event = ev_post.event
            rsvp_users = random.sample(all_users, min(4, len(all_users)))
            for user in rsvp_users:
                RSVP.objects.get_or_create(
                    user=user,
                    event=event,
                    defaults={"status": random.choice(["going", "interested"])},
                )

        self.stdout.write(self.style.SUCCESS("  [+] Interactions : commentaires, reactions, candidatures, RSVP"))

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    def _seed_messages(self, all_users):
        if len(all_users) < 2:
            return

        messages_data = [
            ("Salut ! Tu as vu l'annonce de stage chez Wave ?", "Oui ! Je pense postuler. Et toi ?"),
            ("Bonjour, pouvez-vous me donner plus d'infos sur le poste ?", "Bien sur ! Envoyez-moi votre CV."),
            ("Hello, on se retrouve pour le forum demain ?", "Oui, je serai la a 9h !"),
        ]

        for i, (msg1, msg2) in enumerate(messages_data):
            if i + 1 >= len(all_users):
                break
            user_a = all_users[i]
            user_b = all_users[i + 1]

            # Vérifier si une conversation directe existe déjà
            existing = Conversation.objects.filter(
                conversation_type=Conversation.ConversationType.DIRECT,
                memberships__user=user_a,
            ).filter(memberships__user=user_b).first()

            if existing:
                continue

            conv = Conversation.objects.create(
                conversation_type=Conversation.ConversationType.DIRECT,
                created_by=user_a,
            )
            ConversationParticipant.objects.create(
                conversation=conv, user=user_a,
                role=ConversationParticipant.Role.MEMBER,
            )
            ConversationParticipant.objects.create(
                conversation=conv, user=user_b,
                role=ConversationParticipant.Role.MEMBER,
            )
            Message.objects.create(conversation=conv, sender=user_a, content=msg1)
            Message.objects.create(conversation=conv, sender=user_b, content=msg2)

        self.stdout.write(self.style.SUCCESS("  [+] Conversations directes et messages"))

    # ------------------------------------------------------------------
    # Utilitaire : créer un utilisateur
    # ------------------------------------------------------------------

    def _create_user(self, data, role, is_staff=False):
        user, created = User.objects.get_or_create(
            email=data["email"],
            defaults={
                "username": data["username"],
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "role": role,
                "is_active": True,
                "is_staff": is_staff,
            },
        )
        if created:
            user.set_password(PASSWORD)
            user.save()
            Token.objects.get_or_create(user=user)
        return user
