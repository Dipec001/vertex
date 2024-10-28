from django.db import migrations, models

def populate_streak_date_field(apps, schema_editor):
    Streak = apps.get_model('myapp', 'Streak')
    for streak in Streak.objects.all():
        streak.date = streak.timeStamp.date()
        streak.save(update_fields=['date'])

def remove_streak_duplicates(apps, schema_editor):
    Streak = apps.get_model('myapp', 'Streak')
    duplicates = (
        Streak.objects.values('user', 'timeStamp__date')
        .annotate(max_id=models.Max('id'), count_id=models.Count('id'))
        .filter(count_id__gt=1)
    )
    for duplicate in duplicates:
        Streak.objects.filter(user=duplicate['user'], timeStamp__date=duplicate['timeStamp__date']).exclude(id=duplicate['max_id']).delete()

def remove_dailysteps_duplicates(apps, schema_editor):
    DailySteps = apps.get_model('myapp', 'DailySteps')
    duplicates = (
        DailySteps.objects.values('user', 'timestamp__date')
        .annotate(max_id=models.Max('id'), count_id=models.Count('id'))
        .filter(count_id__gt=1)
    )
    for duplicate in duplicates:
        DailySteps.objects.filter(user=duplicate['user'], timestamp__date=duplicate['timestamp__date']).exclude(id=duplicate['max_id']).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0030_populate_date_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='streak',
            name='date',
            field=models.DateField(null=True),
        ),
        migrations.AddField(
            model_name='dailysteps',
            name='date',
            field=models.DateField(null=True),
        ),
        migrations.RunPython(remove_streak_duplicates),
        migrations.RunPython(populate_streak_date_field),
        migrations.RunPython(remove_dailysteps_duplicates),
        migrations.AlterField(
            model_name='streak',
            name='date',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='dailysteps',
            name='date',
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name='streak',
            name='timeStamp',
            field=models.DateTimeField(),
        ),
        migrations.AlterUniqueTogether(
            name='streak',
            unique_together={('user', 'date')},
        ),
        migrations.AlterUniqueTogether(
            name='dailysteps',
            unique_together={('user', 'date')},
        ),
    ]
