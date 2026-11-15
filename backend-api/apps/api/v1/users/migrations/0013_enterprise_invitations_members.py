"""E5.3: verified company accounts, recruiter memberships and emailed invitations."""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("users", "0012_establishment_invitations_mfa")]

    operations = [
        migrations.AddField(
            model_name="enterprise", name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="enterprise", name="verified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="EnterpriseMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("enterprise", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recruiters", to="users.enterprise")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="enterprise_membership", to=settings.AUTH_USER_MODEL)),
            ],
            options={"indexes": [models.Index(fields=["enterprise", "is_active"], name="users_e53_member_status_idx")]},
        ),
        migrations.CreateModel(
            name="EnterpriseInvitation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(db_index=True, max_length=254)),
                ("kind", models.CharField(choices=[("owner", "Responsable"), ("recruiter", "Recruteur")], max_length=12)),
                ("company_name", models.CharField(blank=True, max_length=255)),
                ("sector", models.CharField(blank=True, max_length=100)),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField()),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("accepted_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="accepted_enterprise_invitations", to=settings.AUTH_USER_MODEL)),
                ("enterprise", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="invitations", to="users.enterprise")),
                ("invited_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sent_enterprise_invitations", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["email", "-created_at"], name="users_e53_inv_email_idx")],
            },
        ),
    ]
