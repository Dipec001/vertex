# Generated by Django 5.1.1 on 2024-12-10 09:44

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0044_remove_customuser_xp_alter_leagueinstance_is_active_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="userleague",
            name="is_retained",
        ),
    ]
