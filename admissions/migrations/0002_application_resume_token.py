# Adds resume_token in 3 steps, per Django's own guidance for unique fields
# with a callable default (https://docs.djangoproject.com/en/6.0/howto/writing-migrations/#migrations-that-add-unique-fields):
# SQLite's table-remake strategy for AddField evaluates a callable default
# once for the whole batch, not per row, so a plain AddField(unique=True,
# default=<callable>) collides on any table with more than one existing row.

from django.db import migrations, models

import admissions.models


def backfill_resume_tokens(apps, schema_editor):
    Application = apps.get_model('admissions', 'Application')
    for application in Application.objects.all():
        application.resume_token = admissions.models.generate_resume_token()
        application.save(update_fields=['resume_token'])


class Migration(migrations.Migration):

    dependencies = [
        ('admissions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='resume_token',
            field=models.CharField(blank=True, default='', editable=False, max_length=48),
        ),
        migrations.RunPython(backfill_resume_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='application',
            name='resume_token',
            field=models.CharField(
                default=admissions.models.generate_resume_token, editable=False, max_length=48, unique=True,
            ),
        ),
    ]
