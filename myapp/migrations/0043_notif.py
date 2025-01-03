# Generated by Django 5.1.1 on 2024-12-07 00:50

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0042_alter_drawimage_image_link"),
    ]

    operations = [
        migrations.CreateModel(
            name="Notif",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("content", models.TextField(max_length=1024)),
                (
                    "notif_type",
                    models.CharField(
                        choices=[
                            ("received_gem", "Received Gem"),
                            ("league_promotion", "League Promotion"),
                            ("league_demotion", "League Demotion"),
                            ("league_retained", "League Retained"),
                            ("purchase_companydraw", "Purchase Company Draw"),
                            ("purchase_globaldraw", "Purchase Global Draw"),
                            ("purchase_streaksaver", "Purchase Streak Saver"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(
                        fields=["user", "created_at"],
                        name="myapp_notif_user_id_0ea98c_idx",
                    )
                ],
            },
        ),
    ]
