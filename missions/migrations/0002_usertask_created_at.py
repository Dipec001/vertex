# Generated by Django 5.1.1 on 2024-12-20 09:53

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("missions", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="usertask",
            name="created_at",
            field=models.DateTimeField(
                default=datetime.datetime(
                    2024, 12, 20, 9, 53, 44, 907345, tzinfo=datetime.timezone.utc
                )
            ),
        ),
    ]