# Generated by Django 5.1.1 on 2024-10-26 06:13

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0026_companyleagueinstance_is_active_customuser_league_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customuser",
            name="league",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="myapp.leagueinstance",
            ),
        ),
    ]
