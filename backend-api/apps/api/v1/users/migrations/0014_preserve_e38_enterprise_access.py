"""Preserve E38 provisioned companies when enabling E53 verification.

This timestamp records grandfathered access, not a new email verification.
Only profiles present at this upgrade are carried forward. Future accounts
still require the E53 invitation flow. No credentials or sessions are changed.
"""
from django.db import migrations
from django.utils import timezone


def preserve_existing_companies(apps, schema_editor):
    Enterprise = apps.get_model("users", "Enterprise")
    Enterprise.objects.using(schema_editor.connection.alias).filter(
        user__role="enterprise", verified_at__isnull=True,
    ).update(verified_at=timezone.now())


class Migration(migrations.Migration):
    dependencies = [("users", "0013_enterprise_invitations_members")]

    operations = [
        migrations.RunPython(preserve_existing_companies, migrations.RunPython.noop),
    ]
