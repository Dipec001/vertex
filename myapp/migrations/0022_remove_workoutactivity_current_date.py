# Generated by Django 5.1.1 on 2024-10-20 08:52

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0021_alter_prize_value"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="workoutactivity",
            name="current_date",
        ),
    ]