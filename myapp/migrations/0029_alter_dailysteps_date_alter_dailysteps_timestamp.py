# Generated by Django 5.1.1 on 2024-10-26 18:31

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0028_rename_xp_userleague_xp_company_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dailysteps",
            name="date",
            field=models.DateField(),
        ),
        migrations.AlterField(
            model_name="dailysteps",
            name="timestamp",
            field=models.DateTimeField(),
        ),
    ]