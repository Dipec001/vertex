# Generated by Django 5.1.1 on 2024-10-19 21:20

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0020_rename_name_draw_draw_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="prize",
            name="value",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
    ]