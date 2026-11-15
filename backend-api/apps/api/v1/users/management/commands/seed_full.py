"""
Peuplement complet et réaliste de la base de données GConnect.

Usage:
  python manage.py seed_full
  python manage.py seed_full --flush       # purge posts/interactions avant de repeupler
  python manage.py seed_full --no-images   # ignore la génération d'images
"""

import io
import os
import random
from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from rest_framework.authtoken.models import Token

from apps.api.v1.core.models import Interest, Preference, Sector, Skill
from apps.api.v1.establishments.models import (
    AlumniInstitution,
    AlumniPromotionMembership,
    Institution,
    Promotion,
    PromotionMembership,
    StudentAccountOrder,
    StudentInstitution,
)
from apps.api.v1.messaging.models import Conversation, ConversationParticipant, Message
from apps.api.v1.posts.models import (
    Application,
    Bookmark,
    Comment,
    Event,
    Opportunity,
    Post,
    PostAttachment,
    Project,
    Reaction,
    RSVP,
)
from apps.api.v1.users.models import Alumni, Enterprise, InstitutionAdmin, Student, User

PASSWORD = "Test@1234"

# ─────────────────────────────────────────────────────────────────────────────
# Données de référence
# ─────────────────────────────────────────────────────────────────────────────

SKILLS_DATA = [
    "Python", "Django", "JavaScript", "TypeScript", "React", "Vue.js",
    "Flutter", "Dart", "Kotlin", "Swift", "Java", "Spring Boot",
    "Node.js", "Express.js", "PHP", "Laravel",
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
    "Docker", "Kubernetes", "CI/CD", "Git", "Linux",
    "Machine Learning", "Data Science", "TensorFlow", "PyTorch",
    "AWS", "Google Cloud", "Azure", "DevOps",
    "UI/UX Design", "Figma", "Adobe XD",
    "Marketing Digital", "SEO", "Gestion de projet", "Agile/Scrum",
    "Communication", "Leadership", "Analyse financière", "Comptabilité",
]

INTERESTS_DATA = [
    "Intelligence Artificielle", "Développement Web", "Développement Mobile",
    "Cybersécurité", "Cloud Computing", "Blockchain",
    "Entrepreneuriat", "Innovation", "Startup",
    "Finance & Fintech", "Santé Numérique", "EdTech",
    "Agriculture Tech", "Energie Renouvelable", "Smart Cities",
    "Sport", "Arts & Culture", "Environnement", "Recherche", "Voyages",
]

PREFERENCES_DATA = [
    "Travail en équipe", "Télétravail", "Startup", "Grande entreprise",
    "ONG", "Secteur public", "Freelance", "Mentorat",
    "Innovation", "Impact social", "Flexibilité", "Évolution rapide",
]

SECTORS_DATA = [
    "Technologie de l'information", "Finance & Banque", "Santé",
    "Éducation", "Agriculture", "Commerce & E-commerce",
    "Énergie", "Télécommunications", "Administration publique",
    "Média & Communication", "Transport & Logistique",
    "Industrie & Manufacture", "Tourisme & Hôtellerie", "BTP",
]

MALE_FIRST_NAMES = [
    "Amadou", "Moussa", "Ibrahim", "Omar", "Cheikh", "Abdoulaye",
    "Mamadou", "Modou", "Alassane", "Boubacar", "Samba", "Lamine",
    "Ousmane", "Papa", "Serigne", "Ibrahima", "Pape", "Malick",
    "Thierno", "Babacar", "Abdou", "Mouhamed", "Seydou", "Aliou", "Daouda",
]

FEMALE_FIRST_NAMES = [
    "Fatou", "Aissatou", "Mariama", "Khady", "Rokhaya", "Ndéye",
    "Aminata", "Coumba", "Binta", "Dieynaba", "Fatoumata", "Nabou",
    "Seynabou", "Sokhna", "Mame", "Awa", "Adja", "Rama", "Yacine", "Ndeye",
    "Mbaye", "Salimata", "Ndoumbe", "Astou", "Bineta",
]

LAST_NAMES = [
    "Diallo", "Sow", "Ba", "Ndiaye", "Fall", "Sy", "Diop",
    "Sarr", "Cissé", "Diouf", "Gueye", "Kane", "Koné", "Mbaye",
    "Ndong", "Niang", "Tall", "Touré", "Wade", "Sall",
    "Badji", "Bodian", "Camara", "Coulibaly", "Faye",
    "Dème", "Dramé", "Kouyaté", "Lô", "Ndoye",
]

# ─────────────────────────────────────────────────────────────────────────────
# 5 établissements avec données complètes
# ─────────────────────────────────────────────────────────────────────────────

INSTITUTIONS_DATA = [
    {
        "name": "Université Cheikh Anta Diop",
        "acronym": "UCAD",
        "address": "Route de Ouakam, Dakar, Sénégal",
        "phone": "+221 33 825 04 44",
        "email": "contact@ucad.sn",
        "website": "https://www.ucad.sn",
        "established_year": 1957,
        "description": (
            "La plus grande université d'Afrique de l'Ouest francophone, "
            "fondée en 1957. Elle forme des étudiants dans de nombreuses disciplines "
            "allant des sciences aux lettres, en passant par la médecine et le droit."
        ),
        "color": "#1D6FA4",
        "text_color": "#FFFFFF",
        "departments": [
            ("Informatique", ["L1", "L2", "L3", "M1", "M2"]),
            ("Mathématiques", ["L1", "L2", "L3", "M1"]),
            ("Physique-Chimie", ["L1", "L2", "L3"]),
            ("Médecine", ["L1", "L2", "L3"]),
            ("Droit", ["L1", "L2", "L3", "M1", "M2"]),
        ],
    },
    {
        "name": "École Supérieure Polytechnique",
        "acronym": "ESP",
        "address": "Fann Résidence, Dakar, Sénégal",
        "phone": "+221 33 821 20 30",
        "email": "contact@esp.sn",
        "website": "https://www.esp.sn",
        "established_year": 1994,
        "description": (
            "Grande école d'ingénieurs de référence au Sénégal, rattachée à l'UCAD. "
            "L'ESP forme des ingénieurs et architectes de haut niveau dans les domaines "
            "du génie informatique, électronique, civil et de l'architecture."
        ),
        "color": "#E74C3C",
        "text_color": "#FFFFFF",
        "departments": [
            ("Génie Informatique", ["L1", "L2", "L3", "M1", "M2"]),
            ("Génie Électronique", ["L1", "L2", "L3", "M1"]),
            ("Génie Civil", ["L1", "L2", "L3", "M1"]),
            ("Architecture", ["L1", "L2", "L3", "M1", "M2"]),
            ("Génie Chimique", ["L1", "L2", "L3"]),
        ],
    },
    {
        "name": "Institut Supérieur de Management",
        "acronym": "ISM",
        "address": "Avenue Bourguiba, Dakar, Sénégal",
        "phone": "+221 33 821 22 22",
        "email": "contact@ism.sn",
        "website": "https://www.ism.sn",
        "established_year": 1992,
        "description": (
            "Premier MBA d'Afrique subsaharienne francophone, l'ISM propose des "
            "formations de haut niveau en management, marketing, finance et ressources humaines. "
            "Fort d'un réseau de plus de 20 000 alumni dans 30 pays."
        ),
        "color": "#27AE60",
        "text_color": "#FFFFFF",
        "departments": [
            ("Marketing & Commerce", ["L1", "L2", "L3", "M1", "M2"]),
            ("Finance & Comptabilité", ["L1", "L2", "L3", "M1", "M2"]),
            ("Ressources Humaines", ["L1", "L2", "M1"]),
            ("Management des SI", ["L1", "L2", "L3", "M1"]),
            ("Entrepreneuriat", ["M1", "M2"]),
        ],
    },
    {
        "name": "Université Gaston Berger",
        "acronym": "UGB",
        "address": "Saint-Louis, Sénégal",
        "phone": "+221 33 961 19 53",
        "email": "contact@ugb.edu.sn",
        "website": "https://www.ugb.edu.sn",
        "established_year": 1990,
        "description": (
            "Créée en 1990, l'Université Gaston Berger de Saint-Louis est reconnue pour "
            "l'excellence de ses formations pluridisciplinaires. Elle est dotée d'un campus "
            "moderne et d'un écosystème propice à la recherche et à l'innovation."
        ),
        "color": "#8E44AD",
        "text_color": "#FFFFFF",
        "departments": [
            ("Sciences Économiques", ["L1", "L2", "L3", "M1", "M2"]),
            ("Informatique Appliquée", ["L1", "L2", "L3", "M1"]),
            ("Lettres & Sciences Humaines", ["L1", "L2", "L3"]),
            ("Sciences Juridiques", ["L1", "L2", "L3", "M1"]),
            ("Mathématiques Appliquées", ["L1", "L2", "L3"]),
        ],
    },
    {
        "name": "Institut Africain de Management",
        "acronym": "IAM",
        "address": "Sacré-Coeur, Dakar, Sénégal",
        "phone": "+221 33 869 58 58",
        "email": "contact@iam.sn",
        "website": "https://www.iam.sn",
        "established_year": 2000,
        "description": (
            "L'IAM est une école de management panafricaine offrant des programmes "
            "accrédités en management, informatique, finance et communication. "
            "Présente dans 8 pays africains, elle prépare les leaders de demain."
        ),
        "color": "#F39C12",
        "text_color": "#FFFFFF",
        "departments": [
            ("Management Général", ["L1", "L2", "L3", "M1", "M2"]),
            ("Informatique de Gestion", ["L1", "L2", "L3", "M1"]),
            ("Communication & Marketing", ["L1", "L2", "L3", "M1"]),
            ("Droit des Affaires", ["L1", "L2", "L3"]),
            ("Finance Internationale", ["M1", "M2"]),
        ],
    },
]

ENTERPRISES_DATA = [
    {
        "username": "sonatel_rh",
        "first_name": "Sonatel",
        "last_name": "RH",
        "email": "careers@sonatel.test",
        "company": "Sonatel",
        "sector": "Télécommunications",
        "website": "https://www.sonatel.sn",
        "color": "#FE6B00",
    },
    {
        "username": "orange_sn",
        "first_name": "Orange",
        "last_name": "Sénégal",
        "email": "talent@orange-sn.test",
        "company": "Orange Sénégal",
        "sector": "Télécommunications",
        "website": "https://www.orange.sn",
        "color": "#FF6600",
    },
    {
        "username": "wave_africa",
        "first_name": "Wave",
        "last_name": "Africa",
        "email": "jobs@wave.test",
        "company": "Wave Africa",
        "sector": "Fintech",
        "website": "https://www.wave.com",
        "color": "#00B4D8",
    },
    {
        "username": "gainde_2000",
        "first_name": "Gainde",
        "last_name": "2000",
        "email": "rh@gainde2000.test",
        "company": "Gainde 2000",
        "sector": "Logistique & Commerce",
        "website": "https://www.gainde2000.sn",
        "color": "#2ECC71",
    },
    {
        "username": "ctic_dakar",
        "first_name": "CTIC",
        "last_name": "Dakar",
        "email": "contact@ctic.test",
        "company": "CTIC Dakar",
        "sector": "Incubateur Tech",
        "website": "https://www.cticdakar.com",
        "color": "#3498DB",
    },
    {
        "username": "teranga_fintech",
        "first_name": "Teranga",
        "last_name": "Fintech",
        "email": "hr@terangafintech.test",
        "company": "Teranga Fintech",
        "sector": "Finance & Technologie",
        "website": "https://www.terangafintech.test",
        "color": "#9B59B6",
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Contenu des publications
# ─────────────────────────────────────────────────────────────────────────────

DISCUSSION_POSTS = [
    # Public
    ("Bienvenue sur G-Connect !", "public",
     "Heureux de rejoindre cette plateforme dédiée aux étudiants et alumni "
     "sénégalais. Qui d'autre est là ? N'hésitez pas à vous présenter en commentaire !"),
    ("Conseils pour décrocher un stage en tech", "public",
     "Je partage 5 conseils pour maximiser vos chances de décrocher un stage "
     "dans le secteur tech au Sénégal :\n\n1. Construisez un portfolio GitHub solide\n"
     "2. Participez aux hackathons locaux\n3. Rejoignez les communautés tech (GDG Dakar, etc.)\n"
     "4. Optimisez votre profil LinkedIn\n5. Candidatez tôt et souvent"),
    ("Retour d'expérience : 6 mois chez Wave Africa", "public",
     "Après 6 mois de stage chez Wave Africa en tant que développeur Flutter, "
     "voici ce que j'ai appris. L'environnement est stimulant, les équipes sont "
     "passionnées et la tech stack est moderne. On travaille avec Flutter pour le "
     "mobile, Python pour les APIs et PostgreSQL pour les données."),
    ("Flutter vs React Native en 2024 : mon avis", "public",
     "Après avoir travaillé avec les deux frameworks, voici ma comparaison honnête. "
     "Flutter gagne en performance et en cohérence UI, mais React Native a un "
     "écosystème JavaScript plus riche. Pour les nouveaux projets en 2024, "
     "je recommande Flutter sans hésitation."),
    ("Comment négocier son salaire de premier emploi ?", "public",
     "Question souvent évitée mais fondamentale : comment négocier son salaire "
     "quand on sort de l'école ? Partagez vos expériences et conseils !"),
    ("Les certifications Cloud les plus demandées en Afrique", "public",
     "D'après mon analyse des offres d'emploi tech en Afrique de l'Ouest, "
     "voici les certifications les plus recherchées :\n\n"
     "☁️ AWS Cloud Practitioner\n☁️ Google Associate Cloud Engineer\n"
     "🔒 CompTIA Security+\n📊 Azure Data Fundamentals"),
    ("Top 10 des startups tech sénégalaises à suivre en 2024", "public",
     "L'écosystème tech sénégalais est en pleine effervescence. "
     "Voici les 10 startups à surveiller cette année : Wave, Yobantel, "
     "JULAYA, InTouch, Paps, Payunit, Yobante Express, DakarFood, "
     "Mlouma, et Weebi. Laquelle connaissez-vous ?"),
    ("Masterclass : Intelligence Artificielle pour débutants", "public",
     "Je lance une série de 10 posts pour expliquer l'IA simplement. "
     "Episode 1 : Qu'est-ce que le Machine Learning ?\n\n"
     "Le ML, c'est la capacité d'un algorithme à apprendre à partir "
     "de données sans être explicitement programmé..."),
    ("Open source : comment contribuer quand on est débutant ?", "public",
     "Contribuer à l'open source est excellent pour votre CV et vos compétences. "
     "Commencez par :\n• Corriger des typos dans la documentation\n"
     "• Reporter des bugs\n• Répondre aux issues\n• Faire des petites corrections de code"),
    ("Data Science avec Python : par où commencer ?", "public",
     "Le chemin d'apprentissage que je recommande pour devenir Data Scientist :\n\n"
     "1. Python + Numpy + Pandas (2 mois)\n2. Visualisation avec Matplotlib/Seaborn\n"
     "3. Machine Learning avec Scikit-learn\n4. Deep Learning avec TensorFlow\n"
     "5. Projets réels sur Kaggle"),

    # Établissement général (general_promotion)
    ("Annonce : Forum de l'emploi 2024", "general_promotion",
     "Nous sommes heureux d'annoncer la tenue du Forum de l'Emploi annuel "
     "le mois prochain. Plus de 50 entreprises seront présentes pour rencontrer "
     "nos étudiants et diplômés. Inscriptions ouvertes sur le portail étudiant."),
    ("Calendrier des examens - Session 2", "general_promotion",
     "Le calendrier des examens de la session 2 est maintenant disponible. "
     "Les examens se dérouleront du 15 au 28 juin 2024. "
     "Consultez votre emploi du temps sur l'ENT et préparez-vous bien !"),
    ("Félicitations à nos lauréats de promotion !", "general_promotion",
     "Nous félicitons chaleureusement les 127 étudiants qui ont brillamment "
     "obtenu leur diplôme lors de la cérémonie de remise de diplômes. "
     "Vous faites la fierté de notre établissement. Bonne chance dans vos projets !"),
    ("Nouveau partenariat avec Google for Education", "general_promotion",
     "Excellente nouvelle ! Notre établissement vient de signer un partenariat "
     "avec Google for Education. Cela permettra à nos étudiants d'accéder "
     "gratuitement aux certifications Google Cloud, Workspace et aux ressources "
     "pédagogiques de Google."),
    ("Rappel : Dépôt des dossiers de bourse avant le 31 mai", "general_promotion",
     "Rappel important : les dossiers de candidature aux bourses d'études "
     "(nationales et internationales) doivent être déposés au Service de Scolarité "
     "avant le 31 mai 2024. N'attendez pas la dernière minute !"),

    # Promotion spécifique (specific_promotion)
    ("Programme du séminaire de fin d'année - M2", "specific_promotion",
     "Chers étudiants de Master 2, voici le programme définitif de notre "
     "séminaire de clôture. Les présentations de projets de fin d'études "
     "auront lieu les 20 et 21 juin. Chaque groupe dispose de 20 minutes "
     "de présentation et 10 minutes de questions. Soyez prêts !"),
    ("Partage de ressources : préparation aux certifications AWS", "specific_promotion",
     "Comme promis, je partage les ressources que j'ai utilisées pour préparer "
     "ma certification AWS :\n📚 AWS Certified Solutions Architect Study Guide\n"
     "🎥 Udemy : A Cloud Guru\n📝 AWS Skill Builder (gratuit)\n"
     "💻 Exercices pratiques sur sandbox AWS"),
    ("Concours d'innovation : inscrivez votre projet !", "specific_promotion",
     "Le concours d'innovation inter-promotions est lancé ! "
     "Les projets doivent résoudre un problème concret lié à notre quotidien. "
     "Dotation : 500 000 FCFA pour le 1er prix. "
     "Date limite d'inscription : 15 juin 2024."),
    ("Sondage : quel sujet pour le prochain workshop ?", "specific_promotion",
     "Nous organisons un workshop mensuel et avons besoin de votre avis sur "
     "le prochain thème. Options :\n"
     "A) Développement d'API REST avec Django\n"
     "B) Introduction à Kubernetes\n"
     "C) Machine Learning avec scikit-learn\n"
     "D) Développement mobile Flutter avancé\n\nVotez en commentaire !"),
    ("Tutoriel : Déployer une app Django sur Heroku", "specific_promotion",
     "Je vais vous guider pas à pas pour déployer votre première application "
     "Django sur Heroku. C'est plus simple qu'il n'y paraît !\n\n"
     "Étape 1 : Installer le CLI Heroku\n"
     "Étape 2 : Configurer votre requirements.txt\n"
     "Étape 3 : Créer un fichier Procfile\n"
     "Étape 4 : Configurer les variables d'environnement..."),
]

EVENTS_DATA = [
    {
        "title": "Forum de l'Emploi & des Stages 2024",
        "content": (
            "La grande rencontre annuelle entre nos étudiants, alumni et les "
            "recruteurs est de retour ! Plus de 50 entreprises partenaires seront "
            "présentes pour vous rencontrer, découvrir vos talents et vous proposer "
            "stages, alternances et CDI.\n\n"
            "✅ Apportez votre CV en plusieurs exemplaires\n"
            "✅ Tenez-vous prêt pour des entretiens sur place\n"
            "✅ Habillez-vous professionnellement"
        ),
        "is_online": False,
        "location_name": "Grand Amphi",
        "city": "Dakar",
        "country": "Sénégal",
        "capacity": 500,
        "days_from_now": 21,
        "duration_hours": 8,
    },
    {
        "title": "Hackathon IA & Innovation Sociale",
        "content": (
            "48 heures pour concevoir des solutions technologiques à impact social !\n\n"
            "Thème : Comment l'IA peut-elle améliorer l'accès aux soins de santé "
            "en Afrique de l'Ouest ?\n\n"
            "Équipes de 3 à 5 personnes. Mentors disponibles. "
            "Lots à gagner : matériel informatique + accompagnement startup."
        ),
        "is_online": False,
        "location_name": "Fablab de l'établissement",
        "city": "Dakar",
        "country": "Sénégal",
        "capacity": 120,
        "days_from_now": 35,
        "duration_hours": 48,
    },
    {
        "title": "Webinaire : Lancer sa carrière dans la Fintech",
        "content": (
            "Comment lancer sa carrière dans le secteur Fintech en Afrique ? "
            "Deux experts partageront leur parcours et répondront à vos questions.\n\n"
            "🎤 Intervenant 1 : CTO de Wave Africa\n"
            "🎤 Intervenant 2 : Head of Product chez Julaya\n\n"
            "Gratuit, sur inscription. Lien de connexion envoyé par email."
        ),
        "is_online": True,
        "online_url": "https://meet.google.com/gconnect-fintech",
        "capacity": 300,
        "days_from_now": 10,
        "duration_hours": 2,
    },
    {
        "title": "Cérémonie de Remise des Diplômes - Promotion 2024",
        "content": (
            "Nous avons le plaisir de vous convier à la cérémonie de remise des "
            "diplômes de la promotion 2024. Une journée inoubliable pour célébrer "
            "vos efforts et marquer le début de votre vie professionnelle.\n\n"
            "Robe académique obligatoire. Entrée gratuite pour 2 invités par lauréat."
        ),
        "is_online": False,
        "location_name": "Salle des Fêtes de l'établissement",
        "city": "Dakar",
        "country": "Sénégal",
        "capacity": 800,
        "days_from_now": 45,
        "duration_hours": 5,
    },
    {
        "title": "Workshop : Développement d'APIs REST avec Django",
        "content": (
            "Atelier pratique de 3 heures pour apprendre à construire des APIs "
            "REST robustes avec Django REST Framework.\n\n"
            "Prérequis : bases de Python et connaissance de HTTP.\n"
            "Matériel requis : ordinateur portable avec Python 3.10+ installé."
        ),
        "is_online": False,
        "location_name": "Salle informatique 204",
        "city": "Dakar",
        "country": "Sénégal",
        "capacity": 30,
        "days_from_now": 7,
        "duration_hours": 3,
    },
    {
        "title": "Conférence : L'IA Générative et l'Avenir du Travail",
        "content": (
            "Comment ChatGPT, Gemini et les autres LLMs vont-ils transformer "
            "nos métiers ? Cette conférence explore les opportunités et défis "
            "pour les professionnels africains dans un monde d'IA générative.\n\n"
            "Intervenant : Chercheur en IA à l'INRIA Saclay."
        ),
        "is_online": True,
        "online_url": "https://meet.google.com/gconnect-ai-conf",
        "capacity": 500,
        "days_from_now": 14,
        "duration_hours": 2,
    },
    {
        "title": "Tournoi Sportif Inter-Promotions",
        "content": (
            "Le tournoi sportif annuel est de retour ! Cette année au programme :\n"
            "⚽ Football\n🏀 Basketball\n🏓 Ping-pong\n♟️ Échecs\n\n"
            "Inscrivez votre équipe avant le 1er juin. "
            "Lots pour les 3 premières équipes de chaque discipline."
        ),
        "is_online": False,
        "location_name": "Complexe Sportif de l'établissement",
        "city": "Dakar",
        "country": "Sénégal",
        "capacity": 200,
        "days_from_now": 30,
        "duration_hours": 8,
    },
]

OPPORTUNITIES_DATA = [
    {
        "title": "Stage Développeur Flutter – Wave Africa",
        "content": (
            "Rejoignez l'équipe produit de Wave Africa et contribuez à l'application "
            "utilisée par des millions de personnes en Afrique de l'Ouest.\n\n"
            "🎯 Missions :\n• Développement de nouvelles fonctionnalités Flutter\n"
            "• Participation aux code reviews\n• Collaboration avec l'équipe backend\n\n"
            "💡 Stack : Flutter, Dart, Python, PostgreSQL, Kubernetes"
        ),
        "category": "internship",
        "location_city": "Dakar",
        "work_mode": "onsite",
        "duration_months": 6,
        "deadline_days": 30,
        "tags": ["Flutter", "Dart", "Mobile", "Fintech"],
    },
    {
        "title": "Ingénieur Backend Python – Sonatel",
        "content": (
            "Sonatel recrute un Ingénieur Backend Python pour rejoindre son équipe "
            "d'engineering et contribuer à des APIs à fort trafic.\n\n"
            "Profil recherché :\n• 2+ ans d'expérience en Python/Django\n"
            "• Maîtrise de PostgreSQL et Redis\n"
            "• Expérience avec les architectures microservices\n\n"
            "Ce que nous offrons :\n• Salaire compétitif\n• Télétravail partiel\n"
            "• Plan de formation continu"
        ),
        "category": "job",
        "location_city": "Dakar",
        "work_mode": "hybrid",
        "contract_type": "permanent",
        "salary_min": 700000,
        "salary_max": 1200000,
        "currency": "XOF",
        "deadline_days": 45,
        "tags": ["Python", "Django", "PostgreSQL", "Redis", "Backend"],
    },
    {
        "title": "Alternance Data Science – Orange Sénégal",
        "content": (
            "Orange Sénégal ouvre une alternance de 12 mois au sein de son "
            "département Data & Intelligence Artificielle.\n\n"
            "Projets possibles :\n• Prédiction de churn client\n"
            "• Analyse des données réseau\n• NLP pour le support client\n\n"
            "Rémunération : stage de niveau ingénieur\n"
            "Formation : Master 1 ou 2 en Data Science, IA ou Mathématiques appliquées"
        ),
        "category": "apprenticeship",
        "location_city": "Dakar",
        "work_mode": "hybrid",
        "duration_months": 12,
        "deadline_days": 20,
        "tags": ["Python", "Machine Learning", "Data Science", "NLP", "IA"],
    },
    {
        "title": "Développeur Full-Stack React/Django – Gainde 2000",
        "content": (
            "Gainde 2000 recherche un développeur Full-Stack passionné pour "
            "moderniser sa plateforme de gestion logistique.\n\n"
            "Responsabilités :\n• Développement de nouvelles fonctionnalités\n"
            "• Migration vers une architecture microservices\n"
            "• Développement d'APIs REST\n\n"
            "Stack : React, TypeScript, Django, PostgreSQL, Docker"
        ),
        "category": "job",
        "location_city": "Dakar",
        "work_mode": "onsite",
        "contract_type": "permanent",
        "salary_min": 500000,
        "salary_max": 800000,
        "currency": "XOF",
        "deadline_days": 35,
        "tags": ["React", "Django", "TypeScript", "Full-Stack"],
    },
    {
        "title": "Stage UX/UI Designer – CTIC Dakar",
        "content": (
            "CTIC Dakar, le premier incubateur tech d'Afrique de l'Ouest, "
            "recherche un stagiaire UX/UI Designer pour soutenir ses startups.\n\n"
            "Missions :\n• Conception d'interfaces utilisateur pour les startups du portefeuille\n"
            "• Réalisation de wireframes et prototypes interactifs\n"
            "• Tests utilisateurs et itérations\n\n"
            "Outils : Figma, Adobe XD, Maze"
        ),
        "category": "internship",
        "location_city": "Dakar",
        "work_mode": "onsite",
        "duration_months": 4,
        "deadline_days": 15,
        "tags": ["UX", "UI", "Figma", "Design", "Startup"],
    },
    {
        "title": "Développeur Mobile Android – Teranga Fintech",
        "content": (
            "Teranga Fintech développe des solutions de paiement mobile pour "
            "l'Afrique. Nous recherchons un développeur Android expérimenté.\n\n"
            "Profil :\n• Kotlin maîtrisé\n• Expérience avec les APIs bancaires\n"
            "• Connaissance de la cryptographie et des protocoles de sécurité\n\n"
            "Avantages : stock-options, télétravail, équipe internationale"
        ),
        "category": "job",
        "location_city": "Dakar",
        "work_mode": "remote",
        "contract_type": "permanent",
        "salary_min": 600000,
        "salary_max": 1000000,
        "currency": "XOF",
        "deadline_days": 25,
        "tags": ["Android", "Kotlin", "Mobile", "Fintech", "Paiement"],
    },
    {
        "title": "Stage Marketing Digital – Orange Sénégal",
        "content": (
            "Rejoignez la direction Marketing d'Orange Sénégal pour un stage "
            "de 6 mois dans le domaine du marketing digital et de la communication.\n\n"
            "Missions :\n• Gestion des réseaux sociaux\n"
            "• Création de contenus digitaux\n"
            "• Analyse des performances (KPIs, reporting)\n"
            "• Participation aux campagnes publicitaires"
        ),
        "category": "internship",
        "location_city": "Dakar",
        "work_mode": "onsite",
        "duration_months": 6,
        "deadline_days": 22,
        "tags": ["Marketing Digital", "Social Media", "Communication", "Analytics"],
    },
    {
        "title": "Ingénieur DevOps – Wave Africa",
        "content": (
            "Wave Africa recherche un ingénieur DevOps pour renforcer son "
            "infrastructure cloud et ses pratiques CI/CD.\n\n"
            "Responsabilités :\n• Gestion des clusters Kubernetes\n"
            "• Mise en place de pipelines CI/CD\n"
            "• Monitoring et alerting (Prometheus, Grafana)\n"
            "• Sécurité de l'infrastructure\n\n"
            "Stack : Kubernetes, Terraform, AWS, GitLab CI, Python"
        ),
        "category": "job",
        "location_city": "Dakar",
        "work_mode": "hybrid",
        "contract_type": "permanent",
        "salary_min": 800000,
        "salary_max": 1500000,
        "currency": "XOF",
        "deadline_days": 40,
        "tags": ["DevOps", "Kubernetes", "AWS", "CI/CD", "Infrastructure"],
    },
]

PROJECTS_DATA = [
    {
        "title": "Application de covoiturage pour étudiants de Dakar",
        "content": (
            "Je développe une application Flutter de covoiturage dédiée aux "
            "étudiants des universités de Dakar. L'objectif est de réduire "
            "les coûts de transport et l'empreinte carbone.\n\n"
            "Fonctionnalités prévues :\n• Mise en relation conducteurs/passagers\n"
            "• Paiement intégré via Wave/Orange Money\n"
            "• Système de notation\n• Chat intégré\n\n"
            "Je cherche des co-développeurs (Flutter + Backend Django)."
        ),
        "required_skills": ["Flutter", "Django", "Google Maps", "Firebase"],
        "status": "active",
    },
    {
        "title": "Plateforme de tutorat peer-to-peer",
        "content": (
            "Projet de plateforme mettant en relation des étudiants avancés "
            "avec des débutants pour du tutorat rémunéré.\n\n"
            "L'idée : les tuteurs fixent leurs tarifs et disponibilités, "
            "les élèves réservent des sessions. Paiement sécurisé via l'app.\n\n"
            "Stack prévu : Next.js + Django REST Framework + PostgreSQL"
        ),
        "required_skills": ["Next.js", "Django", "PostgreSQL", "Stripe API"],
        "status": "active",
    },
    {
        "title": "Système de gestion agricole intelligent",
        "content": (
            "Développement d'un système IoT + IA pour aider les petits agriculteurs "
            "sénégalais à optimiser leurs rendements.\n\n"
            "Fonctionnalités :\n• Capteurs de sol connectés\n"
            "• Prédiction météo locale avec ML\n"
            "• Recommandations de cultures\n"
            "• Application mobile de suivi\n\n"
            "Impact visé : 30% d'augmentation des rendements"
        ),
        "required_skills": ["Python", "IoT", "Machine Learning", "Flutter", "Arduino"],
        "status": "draft",
    },
    {
        "title": "HealthConnect : télémédecine pour zones rurales",
        "content": (
            "Application de télémédecine pour connecter des médecins de Dakar "
            "avec des patients des zones rurales sans accès aux soins.\n\n"
            "Ce projet participera au concours Orange Digital Center 2024. "
            "Nous recherchons des développeurs Flutter, un médecin référent "
            "et un UX Designer.\n\nProjet à impact social fort."
        ),
        "required_skills": ["Flutter", "WebRTC", "Django", "UI/UX Design"],
        "status": "active",
    },
    {
        "title": "Marketplace de services freelance africains",
        "content": (
            "Création d'une plateforme type Upwork/Fiverr mais centrée sur "
            "les freelances africains. L'objectif est de valoriser les "
            "compétences locales à l'échelle continentale.\n\n"
            "Phase 1 : Sénégal, Côte d'Ivoire, Mali\n"
            "Phase 2 : Expansion pan-africaine\n\n"
            "Stack : React, Django, Stripe + Paiements locaux"
        ),
        "required_skills": ["React", "Django", "PostgreSQL", "Payment APIs"],
        "status": "active",
    },
]

COMMENT_TEXTS = [
    "Super initiative, merci pour le partage !",
    "Très intéressant. J'ai une question : comment s'inscrire ?",
    "Je suis intéressé(e), pouvez-vous donner plus de détails ?",
    "Merci pour cette opportunité, je vais postuler dès maintenant !",
    "Excellent contenu, continuez comme ça 👍",
    "Quelqu'un a déjà participé à ce genre d'événement ? Des retours ?",
    "Ce type de poste correspond exactement à mon profil.",
    "Félicitations ! C'est une belle réalisation.",
    "Je partage avec mon réseau, c'est très utile.",
    "Est-ce que c'est ouvert aux étudiants en première année ?",
    "J'ai posé ma candidature hier. J'espère avoir un retour rapidement !",
    "Les conditions d'accès sont vraiment accessibles. Bonne initiative !",
    "Pour compléter ce qui a été dit, j'ajouterais que...",
    "Merci pour ce partage, j'apprends quelque chose de nouveau chaque jour ici.",
    "Qui d'autre va participer ? On pourrait se retrouver sur place.",
    "C'est exactement ce dont j'avais besoin pour préparer mon CV.",
    "J'avais déjà entendu parler de ça mais je ne savais pas comment démarrer.",
    "Belle opportunité ! La stack technique est moderne et intéressante.",
    "J'ai une expérience similaire et je confirme, c'est une excellente entreprise.",
    "Merci pour les ressources partagées, je commence dès ce soir !",
]

REPLY_TEXTS = [
    "Totalement d'accord avec toi !",
    "Merci pour la précision, c'est utile.",
    "Bonne question ! D'après ce que je sais...",
    "Je me posais la même question.",
    "Oui, c'est ouvert à tous les niveaux.",
    "Tu peux m'envoyer un message pour plus d'infos.",
    "Je t'ai répondu en DM !",
    "Exactement, je confirme cette information.",
    "Super, on pourra s'y retrouver alors !",
    "N'hésite pas à me contacter si tu as des questions.",
]


# ─────────────────────────────────────────────────────────────────────────────
# Génération d'images avec Pillow
# ─────────────────────────────────────────────────────────────────────────────

def _hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _lighten(color_hex: str, factor: float = 0.3):
    r, g, b = _hex_to_rgb(color_hex)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return (r, g, b)


def _make_avatar(initials: str, bg_color: str, size: int = 200):
    """Génère un avatar coloré avec initiales."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    img = Image.new("RGB", (size, size), _hex_to_rgb(bg_color))
    draw = ImageDraw.Draw(img)

    # Cercle de fond légèrement plus clair
    margin = size // 10
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=_lighten(bg_color, 0.2),
    )

    # Texte centré
    font_size = size // 3
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), initials, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2
    y = (size - text_h) // 2 - bbox[1]
    draw.text((x, y), initials, fill="#FFFFFF", font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _make_logo(acronym: str, bg_color: str, size: int = 300):
    """Génère un logo établissement avec acronyme."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    img = Image.new("RGB", (size, size), _hex_to_rgb(bg_color))
    draw = ImageDraw.Draw(img)

    # Bordure interne
    border = size // 15
    draw.rectangle(
        [border, border, size - border, size - border],
        outline=_lighten(bg_color, 0.4),
        width=3,
    )

    font_size = max(size // (len(acronym) + 1), 24)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), acronym, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2
    y = (size - text_h) // 2 - bbox[1]
    draw.text((x, y), acronym, fill="#FFFFFF", font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _make_cover(text: str, bg_color: str, width: int = 1200, height: int = 400):
    """Génère une image de couverture."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    # Dégradé simple : couleur principale → version plus claire
    img = Image.new("RGB", (width, height), _hex_to_rgb(bg_color))
    draw = ImageDraw.Draw(img)

    light = _lighten(bg_color, 0.5)
    for x in range(width):
        ratio = x / width
        r = int(_hex_to_rgb(bg_color)[0] * (1 - ratio) + light[0] * ratio)
        g = int(_hex_to_rgb(bg_color)[1] * (1 - ratio) + light[1] * ratio)
        b = int(_hex_to_rgb(bg_color)[2] * (1 - ratio) + light[2] * ratio)
        draw.line([(x, 0), (x, height)], fill=(r, g, b))

    # Texte
    font_size = 48
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()

    wrapped = text if len(text) <= 35 else text[:32] + "..."
    bbox = draw.textbbox((0, 0), wrapped, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (width - text_w) // 2
    y = (height - text_h) // 2 - bbox[1]

    # Ombre portée
    draw.text((x + 2, y + 2), wrapped, fill=(0, 0, 0, 100), font=font)
    draw.text((x, y), wrapped, fill="#FFFFFF", font=font)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# Commande principale
# ─────────────────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Peuple la base de données avec des données de test complètes et réalistes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Purge les posts, commentaires et interactions avant le peuplement",
        )
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="Ignore la génération d'images (plus rapide)",
        )

    def handle(self, *args, **options):
        self.use_images = not options["no_images"]
        self._check_pillow()

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== GConnect - Peuplement complet de la BDD ===\n"
        ))

        if options["flush"]:
            self._flush()

        with transaction.atomic():
            skills, interests, preferences, sectors = self._seed_core()
            institutions = self._seed_institutions()
            promotions_map = self._seed_promotions(institutions)
            admins = self._seed_admins(institutions)
            students = self._seed_students(institutions, promotions_map, skills, interests)
            alumni = self._seed_alumni(institutions, skills, interests)
            enterprises = self._seed_enterprises()

            all_users = (
                admins
                + [s["user"] for s in students]
                + [a["user"] for a in alumni]
                + enterprises
            )

            posts = self._seed_posts(all_users, institutions, promotions_map, enterprises, students)
            self._seed_interactions(posts, all_users, students, enterprises)
            self._seed_messages(all_users)
            self._seed_account_orders(institutions)

        self._print_summary(institutions, promotions_map, all_users, posts, students)
        self.stdout.write(self.style.SUCCESS(f"Mot de passe de tous les comptes : {PASSWORD}"))

    # ─────────────────────────────────────────────────────────────────────────
    # Flush
    # ─────────────────────────────────────────────────────────────────────────

    def _flush(self):
        self.stdout.write(self.style.WARNING("  ! Purge des publications et interactions..."))
        Bookmark.objects.all().delete()
        Reaction.objects.all().delete()
        Comment.objects.all().delete()
        RSVP.objects.all().delete()
        Application.objects.all().delete()
        PostAttachment.objects.all().delete()
        Post.objects.all().delete()
        self.stdout.write(self.style.SUCCESS("  [+] Publications et interactions purgees"))

    # ─────────────────────────────────────────────────────────────────────────
    # Pillow check
    # ─────────────────────────────────────────────────────────────────────────

    def _check_pillow(self):
        if not self.use_images:
            return
        try:
            import PIL  # noqa: F401
        except ImportError:
            self.stdout.write(self.style.WARNING(
                "  ! Pillow non installe. Generation d'images desactivee.\n"
                "     Installez-le avec : pip install Pillow"
            ))
            self.use_images = False

    # ─────────────────────────────────────────────────────────────────────────
    # Core
    # ─────────────────────────────────────────────────────────────────────────

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
        preferences = list(Preference.objects.all())
        sectors = list(Sector.objects.all())

        self.stdout.write(self.style.SUCCESS(
            f"  [+] Core : {len(skills)} skills · {len(interests)} intérêts · "
            f"{len(preferences)} préférences · {len(sectors)} secteurs"
        ))
        return skills, interests, preferences, sectors

    # ─────────────────────────────────────────────────────────────────────────
    # Institutions
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_institutions(self):
        institutions = []
        for data in INSTITUTIONS_DATA:
            inst, created = Institution.objects.get_or_create(
                name=data["name"],
                defaults={
                    "acronym": data["acronym"],
                    "address": data["address"],
                    "phone": data.get("phone", ""),
                    "email": data["email"],
                    "website": data["website"],
                    "established_year": data["established_year"],
                    "description": data["description"],
                    "is_active": True,
                },
            )

            # Images
            if created and self.use_images:
                logo_data = _make_logo(data["acronym"], data["color"])
                if logo_data:
                    inst.logo.save(
                        f"logo_{data['acronym'].lower()}.png",
                        ContentFile(logo_data),
                        save=False,
                    )

                cover_data = _make_cover(data["name"], data["color"])
                if cover_data:
                    inst.cover_image.save(
                        f"cover_{data['acronym'].lower()}.jpg",
                        ContentFile(cover_data),
                        save=False,
                    )

                if logo_data or cover_data:
                    inst.save()

            tag = "créé" if created else "existant"
            self.stdout.write(f"  [{'+' if created else '='  }] Institution {data['acronym']} ({tag})")
            institutions.append(inst)

        self.stdout.write(self.style.SUCCESS(f"  [+] {len(institutions)} établissements"))
        return institutions

    # ─────────────────────────────────────────────────────────────────────────
    # Promotions
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_promotions(self, institutions):
        """
        Retourne un dict { institution.id: [liste de Promotion (hors générale)] }
        """
        promotions_map = {}
        total = 0
        year = 2024

        for inst_data, institution in zip(INSTITUTIONS_DATA, institutions):
            promos = []
            for dept, levels in inst_data["departments"]:
                for level in levels:
                    promo_name = f"{level} {dept} {year}"
                    promo, created = Promotion.objects.get_or_create(
                        name=promo_name,
                        institution=institution,
                        defaults={
                            "year": year,
                            "department": dept,
                            "level": level,
                            "is_general": False,
                            "description": (
                                f"Promotion {level} du département {dept} "
                                f"de {institution.acronym} – Année {year}"
                            ),
                        },
                    )

                    if created and self.use_images:
                        cover_data = _make_cover(
                            f"{level} {dept}",
                            inst_data["color"],
                            width=800, height=300,
                        )
                        if cover_data:
                            promo.cover_image.save(
                                f"promo_{institution.acronym.lower()}_{level.lower()}_{dept[:8].replace(' ', '_').lower()}.jpg",
                                ContentFile(cover_data),
                                save=True,
                            )

                    promos.append(promo)
                    total += 1 if created else 0

            promotions_map[institution.id] = promos

        self.stdout.write(self.style.SUCCESS(
            f"  [+] {total} promotions spécifiques créées (+ 1 générale/établissement auto)"
        ))
        return promotions_map

    # ─────────────────────────────────────────────────────────────────────────
    # Admins établissement
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_admins(self, institutions):
        admins = []
        for i, institution in enumerate(institutions):
            email = f"admin@{institution.acronym.lower()}.test"
            user = self._create_user(
                username=f"admin_{institution.acronym.lower()}",
                first_name="Admin",
                last_name=institution.acronym,
                email=email,
                role="etablissement",
                is_staff=True,
                color="#2C3E50",
                initials="AD",
            )
            if user:
                InstitutionAdmin.objects.get_or_create(
                    user=user, defaults={"institution": institution}
                )
                admins.append(user)

        # SuperAdmin
        super_admin = self._create_user(
            username="superadmin",
            first_name="Super",
            last_name="Admin",
            email="superadmin@gconnect.test",
            role="superAdmin",
            is_staff=True,
            is_superuser=True,
            color="#1A1A2E",
            initials="SA",
        )
        if super_admin:
            admins.append(super_admin)

        self.stdout.write(self.style.SUCCESS(f"  [+] {len(admins)} admins (dont 1 superAdmin)"))
        return admins

    # ─────────────────────────────────────────────────────────────────────────
    # Étudiants
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_students(self, institutions, promotions_map, skills, interests):
        results = []
        STUDENTS_PER_INST = 14  # ~70 étudiants au total
        all_last = list(LAST_NAMES)
        all_male = list(MALE_FIRST_NAMES)
        all_female = list(FEMALE_FIRST_NAMES)
        used_emails = set(User.objects.values_list("email", flat=True))
        counter = 0

        AVATAR_COLORS_M = ["#2980B9", "#16A085", "#8E44AD", "#D35400", "#27AE60"]
        AVATAR_COLORS_F = ["#E91E8C", "#C0392B", "#F39C12", "#1ABC9C", "#9B59B6"]

        for inst_idx, institution in enumerate(institutions):
            inst_promos = promotions_map.get(institution.id, [])
            created_in_inst = 0

            for s_idx in range(STUDENTS_PER_INST):
                gender = "F" if s_idx % 2 == 0 else "M"
                first = random.choice(all_female if gender == "F" else all_male)
                last = random.choice(all_last)
                slug = f"{first.lower().replace('é','e').replace('è','e').replace('ê','e').replace('ô','o').replace('â','a').replace('î','i').replace('û','u')}"
                email = f"{slug}.{last.lower()}_{counter}@students.test"

                if email in used_emails:
                    counter += 1
                    email = f"{slug}.{last.lower()}_{counter}@students.test"

                used_emails.add(email)
                color = random.choice(AVATAR_COLORS_F if gender == "F" else AVATAR_COLORS_M)
                initials = f"{first[0]}{last[0]}"

                user = self._create_user(
                    username=f"{slug}_{last.lower()}_{counter}",
                    first_name=first,
                    last_name=last,
                    email=email,
                    role="student",
                    color=color,
                    initials=initials,
                )

                if not user:
                    counter += 1
                    continue

                student, _ = Student.objects.get_or_create(
                    user=user,
                    defaults={
                        "gender": gender,
                        "date_of_birth": date(
                            random.randint(1999, 2004),
                            random.randint(1, 12),
                            random.randint(1, 28),
                        ),
                        "student_id": f"STU{inst_idx:02d}{counter:04d}",
                    },
                )

                if skills:
                    student.skills.set(random.sample(skills, min(5, len(skills))))
                if interests:
                    student.interests.set(random.sample(interests, min(4, len(interests))))

                # Rattacher à l'établissement (déclenche le signal → promo générale)
                StudentInstitution.objects.get_or_create(
                    student=student, institution=institution
                )

                # Rattacher à 1 ou 2 promotions spécifiques
                if inst_promos:
                    chosen = random.sample(inst_promos, min(2, len(inst_promos)))
                    for promo in chosen:
                        PromotionMembership.objects.get_or_create(
                            student=student,
                            promotion=promo,
                            defaults={"is_approved": True},
                        )

                results.append({"user": user, "student": student, "institution": institution})
                counter += 1
                created_in_inst += 1

            self.stdout.write(
                f"  [+] {created_in_inst} étudiants créés pour {institution.acronym}"
            )

        self.stdout.write(self.style.SUCCESS(f"  [+] {len(results)} étudiants au total"))
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Alumni
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_alumni(self, institutions, skills, interests):
        results = []
        ALUMNI_PER_INST = 4
        used_emails = set(User.objects.values_list("email", flat=True))
        counter = 0
        AVATAR_COLORS = ["#2C3E50", "#7F8C8D", "#34495E", "#1A237E", "#4A148C"]

        for inst_idx, institution in enumerate(institutions):
            for a_idx in range(ALUMNI_PER_INST):
                gender = "F" if a_idx % 2 == 0 else "M"
                first = random.choice(FEMALE_FIRST_NAMES if gender == "F" else MALE_FIRST_NAMES)
                last = random.choice(LAST_NAMES)
                slug = first.lower().replace("é", "e").replace("è", "e").replace("ê", "e")
                email = f"{slug}.{last.lower()}_alumni_{counter}@alumni.test"

                if email in used_emails:
                    counter += 1
                    email = f"{slug}.{last.lower()}_alumni_{counter}@alumni.test"
                used_emails.add(email)

                color = random.choice(AVATAR_COLORS)
                user = self._create_user(
                    username=f"{slug}_{last.lower()}_alumni_{counter}",
                    first_name=first,
                    last_name=last,
                    email=email,
                    role="alumni",
                    color=color,
                    initials=f"{first[0]}{last[0]}",
                )

                if not user:
                    counter += 1
                    continue

                alumni_obj, _ = Alumni.objects.get_or_create(
                    user=user,
                    defaults={
                        "gender": gender[0],
                        "graduation_date": date(
                            random.randint(2016, 2022),
                            random.randint(5, 8),
                            random.randint(1, 28),
                        ),
                        "institution": institution,
                        "proof_document": "",
                    },
                )

                if skills:
                    alumni_obj.skills.set(random.sample(skills, min(6, len(skills))))
                if interests:
                    alumni_obj.interests.set(random.sample(interests, min(4, len(interests))))

                AlumniInstitution.objects.get_or_create(
                    alumni=alumni_obj, institution=institution
                )

                results.append({"user": user, "alumni": alumni_obj})
                counter += 1

        self.stdout.write(self.style.SUCCESS(f"  [+] {len(results)} alumni"))
        return results

    # ─────────────────────────────────────────────────────────────────────────
    # Entreprises
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_enterprises(self):
        users = []
        for data in ENTERPRISES_DATA:
            user = self._create_user(
                username=data["username"],
                first_name=data["first_name"],
                last_name=data["last_name"],
                email=data["email"],
                role="enterprise",
                color=data.get("color", "#95A5A6"),
                initials=data["first_name"][:2].upper(),
            )
            if user:
                Enterprise.objects.get_or_create(
                    user=user,
                    defaults={
                        "company_name": data["company"],
                        "sector": data["sector"],
                        "website": data.get("website", ""),
                    },
                )
                users.append(user)

        self.stdout.write(self.style.SUCCESS(f"  [+] {len(users)} entreprises"))
        return users

    # ─────────────────────────────────────────────────────────────────────────
    # Publications
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_posts(self, all_users, institutions, promotions_map, enterprise_users, students):
        posts = []

        # ── Discussions variées ──
        self.stdout.write("  > Creation des discussions...")
        non_enterprise = [u for u in all_users if u not in enterprise_users]

        for i, (title, audience, content) in enumerate(DISCUSSION_POSTS):
            author = non_enterprise[i % len(non_enterprise)]
            institution = self._get_user_institution(author, students, institutions)
            promos = promotions_map.get(institution.id, []) if institution else []

            post, created = Post.objects.get_or_create(
                title=title,
                author=author,
                defaults={
                    "content": content,
                    "post_type": Post.PostType.DISCUSSION,
                    "audience": audience,
                    "institution": institution,
                },
            )
            if created:
                self._backdate(post, random.randint(1, 60))
                if audience == "specific_promotion" and promos:
                    post.promotion_targets.set([random.choice(promos)])

            posts.append(post)

        # ── Discussions supplémentaires par institution ──
        EXTRA_INST_POSTS = [
            "📢 Résultats des élections du BDE : voici le nouveau bureau !",
            "📚 Ressources pédagogiques partagées par la bibliothèque universitaire",
            "🏆 Notre équipe au Hackathon National – Résultats et retours",
            "📋 Sondage : satisfaction des étudiants – Répondez avant vendredi",
            "🔧 Maintenance de l'ENT ce weekend – Prévoir des alternatives",
            "🎉 Félicitations à nos 3 étudiants sélectionnés pour la bourse Erasmus+ !",
            "📣 Réunion pédagogique obligatoire vendredi à 14h – Salle amphi B",
            "💡 Idée : créer un club d'entrepreneuriat ? Qui est partant ?",
        ]

        for inst in institutions:
            admin_qs = User.objects.filter(
                role="etablissement", institution_admin_profile__institution=inst
            )
            admin_user = admin_qs.first()
            if not admin_user:
                continue

            inst_promos = promotions_map.get(inst.id, [])

            for i, title in enumerate(EXTRA_INST_POSTS):
                aud = "general_promotion" if i % 3 != 2 else "specific_promotion"
                post, created = Post.objects.get_or_create(
                    title=f"[{inst.acronym}] {title}",
                    author=admin_user,
                    defaults={
                        "content": (
                            f"Publication officielle de {inst.name}.\n\n"
                            + title.lstrip("📢📚🏆📋🔧🎉📣💡 ")
                            + "\n\nPour toute question, contactez le secrétariat."
                        ),
                        "post_type": Post.PostType.DISCUSSION,
                        "audience": aud,
                        "institution": inst,
                    },
                )
                if created:
                    self._backdate(post, random.randint(1, 45))
                    if aud == "specific_promotion" and inst_promos:
                        post.promotion_targets.set([random.choice(inst_promos)])
                posts.append(post)

        # ── Opportunités ──
        self.stdout.write("  > Creation des opportunites...")
        for i, opp_data in enumerate(OPPORTUNITIES_DATA):
            author = enterprise_users[i % len(enterprise_users)] if enterprise_users else all_users[0]
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
                self._backdate(post, random.randint(1, 20))
                opp_kwargs = {
                    "post": post,
                    "category": opp_data["category"],
                    "location_city": opp_data.get("location_city", "Dakar"),
                    "location_country": "Sénégal",
                    "work_mode": opp_data.get("work_mode", "onsite"),
                    "status": Opportunity.Status.OPEN,
                    "deadline": date.today() + timedelta(days=opp_data.get("deadline_days", 30)),
                    "tags": opp_data.get("tags", []),
                    "duration_months": opp_data.get("duration_months"),
                    "contract_type": opp_data.get("contract_type", ""),
                    "salary_min": opp_data.get("salary_min"),
                    "salary_max": opp_data.get("salary_max"),
                    "currency": opp_data.get("currency", "XOF"),
                }
                Opportunity.objects.create(**opp_kwargs)
            posts.append(post)

        # ── Événements ──
        self.stdout.write("  > Creation des evenements...")
        for i, ev_data in enumerate(EVENTS_DATA):
            institution = institutions[i % len(institutions)]
            admin_qs = User.objects.filter(
                role="etablissement", institution_admin_profile__institution=institution
            )
            author = admin_qs.first() or all_users[0]

            post, created = Post.objects.get_or_create(
                title=ev_data["title"],
                author=author,
                defaults={
                    "content": ev_data["content"],
                    "post_type": Post.PostType.EVENT,
                    "audience": "general_promotion" if not ev_data.get("is_online") else Post.Audience.PUBLIC,
                    "institution": institution,
                },
            )
            if created:
                self._backdate(post, random.randint(1, 15))
                Event.objects.create(
                    post=post,
                    starts_at=timezone.now() + timedelta(days=ev_data["days_from_now"]),
                    ends_at=timezone.now() + timedelta(
                        days=ev_data["days_from_now"],
                        hours=ev_data["duration_hours"],
                    ),
                    is_online=ev_data.get("is_online", False),
                    location_name=ev_data.get("location_name", ""),
                    city=ev_data.get("city", ""),
                    country=ev_data.get("country", ""),
                    online_url=ev_data.get("online_url", ""),
                    capacity=ev_data.get("capacity"),
                )
            posts.append(post)

        # ── Projets ──
        self.stdout.write("  > Creation des projets...")
        non_ent_non_admin = [
            u for u in all_users
            if u not in enterprise_users and u.role not in ("etablissement", "superAdmin")
        ]

        for i, proj_data in enumerate(PROJECTS_DATA):
            author = non_ent_non_admin[i % len(non_ent_non_admin)] if non_ent_non_admin else all_users[0]
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
                self._backdate(post, random.randint(5, 40))
                Project.objects.create(
                    post=post,
                    status=proj_data.get("status", "active"),
                    looking_for_members=True,
                    required_skills=proj_data["required_skills"],
                )
            posts.append(post)

        self.stdout.write(self.style.SUCCESS(f"  [+] {len(posts)} publications créées"))
        return posts

    # ─────────────────────────────────────────────────────────────────────────
    # Interactions
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_interactions(self, posts, all_users, students, enterprise_users):
        self.stdout.write("  > Generation des interactions...")
        reaction_kinds = list(Reaction.Kind.values)
        comment_count = 0
        reply_count = 0
        reaction_count = 0
        bookmark_count = 0

        for i, post in enumerate(posts):
            # ── Réactions (4–12 par post) ──
            nb_reactions = random.randint(4, 12)
            reactors = random.sample(all_users, min(nb_reactions, len(all_users)))
            for user in reactors:
                if user == post.author:
                    continue
                r, created = Reaction.objects.get_or_create(
                    user=user, post=post,
                    defaults={"kind": random.choice(reaction_kinds)},
                )
                if created:
                    reaction_count += 1

            # ── Commentaires (2–6 par post) ──
            nb_comments = random.randint(2, 6)
            commenters = random.sample(all_users, min(nb_comments, len(all_users)))
            root_comments = []
            for j, user in enumerate(commenters):
                text = COMMENT_TEXTS[(i + j) % len(COMMENT_TEXTS)]
                comment, created = Comment.objects.get_or_create(
                    user=user, post=post, content=text,
                    defaults={"parent": None},
                )
                if created:
                    comment_count += 1
                root_comments.append(comment)

            # ── Réponses aux commentaires (0–2 par commentaire) ──
            for comment in root_comments[:3]:
                nb_replies = random.randint(0, 2)
                repliers = random.sample(all_users, min(nb_replies, len(all_users)))
                for user in repliers:
                    text = REPLY_TEXTS[random.randint(0, len(REPLY_TEXTS) - 1)]
                    reply, created = Comment.objects.get_or_create(
                        user=user, post=post, content=text,
                        defaults={"parent": comment},
                    )
                    if created:
                        reply_count += 1

            # ── Bookmarks (30 % des posts) ──
            if random.random() < 0.3:
                bm_users = random.sample(all_users, min(random.randint(1, 4), len(all_users)))
                for user in bm_users:
                    bm, created = Bookmark.objects.get_or_create(user=user, post=post)
                    if created:
                        bookmark_count += 1

        # ── Candidatures aux opportunités ──
        app_count = 0
        opp_posts = [p for p in posts if p.post_type == Post.PostType.OPPORTUNITY]
        for opp_post in opp_posts:
            if not hasattr(opp_post, "opportunity"):
                continue
            opp = opp_post.opportunity
            applicants = random.sample(students, min(random.randint(3, 8), len(students)))
            for item in applicants:
                app, created = Application.objects.get_or_create(
                    user=item["user"],
                    opportunity=opp,
                    defaults={
                        "cover_letter": (
                            f"Bonjour,\n\nJe vous soumets ma candidature pour le poste de "
                            f"{opp_post.title}. Mon profil correspond à vos attentes et je suis "
                            f"très motivé(e) pour rejoindre votre équipe.\n\n"
                            f"Cordialement,\n{item['user'].get_full_name()}"
                        ),
                        "status": random.choice(["submitted", "viewed", "shortlisted"]),
                    },
                )
                if created:
                    app_count += 1

        # ── RSVPs aux événements ──
        rsvp_count = 0
        event_posts = [p for p in posts if p.post_type == Post.PostType.EVENT]
        rsvp_pool = [
            u for u in all_users
            if u not in [u for u in all_users if u.role in ("enterprise",)]
        ]
        for ev_post in event_posts:
            if not hasattr(ev_post, "event"):
                continue
            event = ev_post.event
            nb_rsvp = random.randint(5, 20)
            rsvp_users = random.sample(rsvp_pool, min(nb_rsvp, len(rsvp_pool)))
            for user in rsvp_users:
                rsvp, created = RSVP.objects.get_or_create(
                    user=user, event=event,
                    defaults={"status": random.choice(["going", "going", "interested"])},
                )
                if created:
                    rsvp_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"  [+] Interactions : {reaction_count} réactions · "
            f"{comment_count} commentaires · {reply_count} réponses · "
            f"{bookmark_count} favoris · {app_count} candidatures · "
            f"{rsvp_count} RSVP"
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # Messages
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_messages(self, all_users):
        if len(all_users) < 2:
            return

        CONV_MESSAGES = [
            ("Salut ! Tu as vu l'annonce de stage chez Wave ? Tu penses postuler ?",
             "Oui, j'ai vu ! Je prépare mon CV ce soir. Et toi ?"),
            ("Bonjour, je vous contacte concernant le poste que vous avez publié.",
             "Bonjour, bien sûr ! Envoyez-moi votre CV et lettre de motivation."),
            ("Hello, on se retrouve au Forum de l'Emploi demain ?",
             "Oui ! Je serai là dès 9h. On se retrouve à l'entrée ?"),
            ("Tu as des ressources pour préparer la certification AWS ?",
             "Oui ! Je t'envoie mes notes et les liens utiles."),
            ("Félicitations pour ton stage ! Comment ça se passe ?",
             "Merci ! C'est super intéressant, j'apprends énormément chaque jour."),
        ]

        created_count = 0
        for i, (msg1, msg2) in enumerate(CONV_MESSAGES):
            if i * 2 + 1 >= len(all_users):
                break
            user_a = all_users[i * 2]
            user_b = all_users[i * 2 + 1]

            existing = (
                Conversation.objects.filter(
                    conversation_type=Conversation.ConversationType.DIRECT,
                    memberships__user=user_a,
                )
                .filter(memberships__user=user_b)
                .first()
            )
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
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"  [+] {created_count} conversations directes créées"))

    # ─────────────────────────────────────────────────────────────────────────
    # Commandes de comptes étudiant
    # ─────────────────────────────────────────────────────────────────────────

    def _seed_account_orders(self, institutions):
        for institution in institutions:
            StudentAccountOrder.objects.get_or_create(
                institution=institution,
                year=2024,
                defaults={
                    "quantity": 200,
                    "price_per_account": 0,
                    "status": "approved",
                    "used_accounts": random.randint(50, 180),
                },
            )
        self.stdout.write(self.style.SUCCESS(f"  [+] {len(institutions)} commandes de comptes approuvées"))

    # ─────────────────────────────────────────────────────────────────────────
    # Résumé
    # ─────────────────────────────────────────────────────────────────────────

    def _print_summary(self, institutions, promotions_map, all_users, posts, students):
        total_promos = sum(len(v) for v in promotions_map.values())
        total_general = Institution.objects.count()
        membership_count = PromotionMembership.objects.count()
        comment_count = Comment.objects.filter(parent__isnull=True).count()
        reply_count = Comment.objects.filter(parent__isnull=False).count()
        reaction_count = Reaction.objects.count()
        bookmark_count = Bookmark.objects.count()
        app_count = Application.objects.count()
        rsvp_count = RSVP.objects.count()

        self.stdout.write(self.style.MIGRATE_HEADING(
            "\n=== RESUME DU PEUPLEMENT ==="
        ))

        rows = [
            ("Etablissements", len(institutions)),
            ("Promotions generales (auto)", total_general),
            ("Promotions specifiques", total_promos),
            ("Appartenances aux promotions", membership_count),
            ("Utilisateurs (total)", User.objects.count()),
            ("  Admins etablissement", User.objects.filter(role="etablissement").count()),
            ("  Super Admins", User.objects.filter(role="superAdmin").count()),
            ("  Etudiants", User.objects.filter(role="student").count()),
            ("  Alumni", User.objects.filter(role="alumni").count()),
            ("  Entreprises", User.objects.filter(role="enterprise").count()),
            ("Publications (total)", Post.objects.count()),
            ("  Discussions", Post.objects.filter(post_type="discussion").count()),
            ("  Opportunites", Post.objects.filter(post_type="opportunity").count()),
            ("  Evenements", Post.objects.filter(post_type="event").count()),
            ("  Projets", Post.objects.filter(post_type="project").count()),
            ("  Audience publique", Post.objects.filter(audience="public").count()),
            ("  Audience etablissement", Post.objects.filter(audience="general_promotion").count()),
            ("  Audience promo specifique", Post.objects.filter(audience="specific_promotion").count()),
            ("Commentaires", comment_count),
            ("Reponses aux commentaires", reply_count),
            ("Reactions", reaction_count),
            ("Favoris (bookmarks)", bookmark_count),
            ("Candidatures", app_count),
            ("RSVP evenements", rsvp_count),
        ]

        for label, value in rows:
            self.stdout.write(f"  {label:<42} {value}")

        self.stdout.write(self.style.SUCCESS(
            "\n  Mot de passe universel : Test@1234\n"
            "  Peuplement termine avec succes !\n"
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # Utilitaires
    # ─────────────────────────────────────────────────────────────────────────

    def _backdate(self, post: Post, days: int):
        """
        Contourne auto_now_add=True en backdatant created_at via update().
        Cela ne déclenche pas les signaux, ce qui est le comportement voulu.
        """
        past = timezone.now() - timedelta(days=days, hours=random.randint(0, 23))
        Post.objects.filter(pk=post.pk).update(created_at=past)

    def _create_user(
        self, username, first_name, last_name, email, role,
        is_staff=False, is_superuser=False, color="#2C3E50", initials="U",
    ):
        # Cherche d'abord par email, puis par username (évite les doublons entre seeders)
        existing = User.objects.filter(email=email).first()
        if not existing:
            existing = User.objects.filter(username=username[:150]).first()
        if existing:
            return existing

        # Garantit l'unicité du username si un autre utilisateur l'a déjà pris
        base_username = username[:140]
        final_username = base_username
        suffix = 1
        while User.objects.filter(username=final_username).exists():
            final_username = f"{base_username}_{suffix}"
            suffix += 1

        user = User(
            email=email,
            username=final_username,
            first_name=first_name,
            last_name=last_name,
            role=role,
            is_active=True,
            is_staff=is_staff,
            is_superuser=is_superuser,
        )
        user.set_password(PASSWORD)

        if self.use_images:
            avatar_data = _make_avatar(initials.upper(), color)
            if avatar_data:
                user.photo.save(
                    f"avatar_{final_username[:30]}.png",
                    ContentFile(avatar_data),
                    save=False,
                )

        user.save()
        Token.objects.get_or_create(user=user)
        return user

    def _get_user_institution(self, user, students, institutions):
        """Retrouve l'établissement principal d'un utilisateur."""
        if user.role == "student":
            match = next(
                (s for s in students if s["user"] == user), None
            )
            return match["institution"] if match else random.choice(institutions)
        if user.role == "etablissement":
            try:
                return user.institution_admin_profile.institution
            except Exception:
                pass
        if user.role == "alumni":
            try:
                return user.alumni_profile.institution
            except Exception:
                pass
        return random.choice(institutions)
