# E3.2 - privileged web sessions, isolated from legacy Flutter tokens.
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0010_alter_user_is_active_alter_user_is_banned_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="EstablishmentWebSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token_hash", models.CharField(db_index=True, max_length=64, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("last_seen_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField()),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=500)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="establishment_web_sessions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["user", "-created_at"], name="users_web_user_created_e3_idx")],
            },
        ),
    ]
