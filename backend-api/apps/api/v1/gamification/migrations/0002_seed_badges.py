from django.db import migrations

BADGES = [
    dict(code="profil_complet", name="Profil complet", description="Photo, bio, compétences et centres d'intérêt renseignés.",
         icon_emoji="✅", tier="bronze", xp_reward=20),
    dict(code="premiere_publication", name="Première publication", description="A publié son premier post.",
         icon_emoji="📝", tier="bronze", xp_reward=10),
    dict(code="auteur_prolifique", name="Auteur prolifique", description="A publié au moins 10 publications.",
         icon_emoji="✍️", tier="silver", xp_reward=50),
    dict(code="reseauteur", name="Réseauteur", description="A établi au moins 10 relations.",
         icon_emoji="🤝", tier="silver", xp_reward=50),
    dict(code="reseauteur_confirme", name="Réseauteur confirmé", description="A établi au moins 50 relations.",
         icon_emoji="🌐", tier="gold", xp_reward=150),
    dict(code="publication_populaire", name="Publication populaire", description="Une publication a reçu au moins 20 réactions.",
         icon_emoji="🔥", tier="gold", xp_reward=100),
]


def seed_badges(apps, schema_editor):
    Badge = apps.get_model("gamification", "Badge")
    for data in BADGES:
        Badge.objects.get_or_create(code=data["code"], defaults=data)


def remove_badges(apps, schema_editor):
    Badge = apps.get_model("gamification", "Badge")
    Badge.objects.filter(code__in=[b["code"] for b in BADGES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("gamification", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_badges, remove_badges),
    ]
