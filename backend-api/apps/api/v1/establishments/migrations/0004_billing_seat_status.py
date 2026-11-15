"""Keep billable seat activation separate from a member's feed preferences."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("establishments", "0003_alumnipromotionmembership_is_active_and_more")]
    operations = [
        migrations.AddField(
            model_name="studentinstitution", name="seat_enabled",
            field=models.BooleanField(default=True, verbose_name="Compte autorisé par l'établissement"),
        ),
        migrations.AddField(
            model_name="alumniinstitution", name="seat_enabled",
            field=models.BooleanField(default=True, verbose_name="Compte autorisé par l'établissement"),
        ),
    ]
