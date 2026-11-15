import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        ('establishments', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('users', '0001_initial'),
    ]

    operations = [
        # Add establishment FKs to Alumni
        migrations.AddField(
            model_name='alumni',
            name='institution',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='establishments.institution'),
        ),
        migrations.AddField(
            model_name='alumni',
            name='promotion',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='establishments.promotion'),
        ),
        # Add establishment FK to InstitutionAdmin
        migrations.AddField(
            model_name='institutionadmin',
            name='institution',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='establishments.institution'),
        ),
        # Add M2M fields to Alumni
        migrations.AddField(
            model_name='alumni',
            name='interests',
            field=models.ManyToManyField(blank=True, related_name='alumni_interested', to='core.interest'),
        ),
        migrations.AddField(
            model_name='alumni',
            name='preferences',
            field=models.ManyToManyField(blank=True, related_name='alumni_with_preferences', to='core.preference'),
        ),
        migrations.AddField(
            model_name='alumni',
            name='sectors',
            field=models.ManyToManyField(blank=True, related_name='alumni_in_sectors', to='core.sector'),
        ),
        migrations.AddField(
            model_name='alumni',
            name='skills',
            field=models.ManyToManyField(blank=True, related_name='alumni_with_skills', to='core.skill'),
        ),
        # Add M2M fields to Student
        migrations.AddField(
            model_name='student',
            name='interests',
            field=models.ManyToManyField(blank=True, related_name='students_interested', to='core.interest'),
        ),
        migrations.AddField(
            model_name='student',
            name='preferences',
            field=models.ManyToManyField(blank=True, related_name='students_with_preferences', to='core.preference'),
        ),
        migrations.AddField(
            model_name='student',
            name='sectors',
            field=models.ManyToManyField(blank=True, related_name='students_in_sectors', to='core.sector'),
        ),
        migrations.AddField(
            model_name='student',
            name='skills',
            field=models.ManyToManyField(blank=True, related_name='students_with_skills', to='core.skill'),
        ),
        migrations.AddField(
            model_name='student',
            name='institutions',
            field=models.ManyToManyField(related_name='students', through='establishments.StudentInstitution', to='establishments.institution'),
        ),
    ]
