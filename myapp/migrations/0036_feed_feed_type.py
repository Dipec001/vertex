# Generated by Django 5.1.1 on 2024-11-12 01:00

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0035_feed_clap_userfollowing"),
    ]

    operations = [
        migrations.AddField(
            model_name="feed",
            name="feed_type",
            field=models.CharField(
                choices=[
                    ("Promotion", "Promotion"),
                    ("Milestone", "Milestone"),
                    ("Streak", "Streak"),
                    ("Prize", "Prize"),
                ],
                default="Streak",
                max_length=30,
            ),
            preserve_default=False,
        ),
    ]
