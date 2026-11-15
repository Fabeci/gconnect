"""E4 audit action labels."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("core", "0006_alter_auditlogentry_action")]

    operations = [
        migrations.AlterField(
            model_name="auditlogentry",
            name="action",
            field=models.CharField(
                choices=[("login_success", "Connexion réussie"), ("login_failed", "Connexion échouée"), ("logout", "Déconnexion"), ("password_changed", "Mot de passe modifié"), ("sessions_revoked", "Sessions révoquées"), ("privacy_updated", "Confidentialité modifiée"), ("data_exported", "Données personnelles exportées"), ("account_deleted", "Compte supprimé"), ("report_reviewed", "Signalement examiné"), ("post_hidden", "Publication masquée par modération"), ("user_banned", "Utilisateur banni"), ("user_unbanned", "Utilisateur débanni"), ("import_completed", "Import massif effectué"), ("api_key_created", "Clé API créée"), ("api_key_revoked", "Clé API révoquée"), ("invitation_sent", "Invitation envoyée"), ("invitation_revoked", "Invitation révoquée"), ("invitation_accepted", "Invitation acceptée"), ("mfa_challenge_issued", "Contrôle MFA requis"), ("mfa_success", "Double authentification réussie")],
                db_index=True, max_length=32,
            ),
        ),
    ]
