# Generated by Django 5.1.1 on 2024-12-04 03:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0040_gem_copy_manual_gem_gem_copy_xp_gem"),
    ]

    operations = [
        migrations.CreateModel(
            name="DrawImage",
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
                ("image_link", models.ImageField(upload_to="draw_images/")),
                ("title", models.CharField(max_length=255)),
                (
                    "draw",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to="myapp.draw",
                    ),
                ),
            ],
        ),
    ]