# Generated by Django 5.1.1 on 2024-11-04 09:00

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0032_alter_xp_timestamp"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dailysteps",
            name="xp",
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name="workoutactivity",
            name="xp",
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name="xp",
            name="totalXpAllTime",
            field=models.IntegerField(default=0.0),
        ),
        migrations.AlterField(
            model_name="xp",
            name="totalXpToday",
            field=models.IntegerField(default=0.0),
        ),
        migrations.AlterUniqueTogether(
            name="workoutactivity",
            unique_together={("user", "start_datetime")},
        ),
    ]