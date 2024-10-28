from django.db import migrations, models

def populate_date_field(apps, schema_editor):
    Xp = apps.get_model('myapp', 'Xp')
    for xp in Xp.objects.all():
        # Extract the date part from timeStamp and assign to date field
        xp.date = xp.timeStamp.date()
        xp.save(update_fields=['date'])

def remove_duplicates(apps, schema_editor):
    Xp = apps.get_model('myapp', 'Xp')
    duplicates = (
        Xp.objects.values('user', 'timeStamp__date')
        .annotate(max_id=models.Max('id'), count_id=models.Count('id'))
        .filter(count_id__gt=1)
    )

    for duplicate in duplicates:
        # Keep the latest record and delete the others
        Xp.objects.filter(user=duplicate['user'], timeStamp__date=duplicate['timeStamp__date']).exclude(id=duplicate['max_id']).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0029_alter_dailysteps_date_alter_dailysteps_timestamp'),
    ]

    operations = [
        migrations.AddField(
            model_name='xp',
            name='date',
            field=models.DateField(null=True),
        ),
        migrations.RunPython(remove_duplicates),
        migrations.RunPython(populate_date_field),
        migrations.AlterField(
            model_name='xp',
            name='date',
            field=models.DateField(),
        ),
        migrations.AlterUniqueTogether(
            name='xp',
            unique_together={('user', 'date')},
        ),
    ]
