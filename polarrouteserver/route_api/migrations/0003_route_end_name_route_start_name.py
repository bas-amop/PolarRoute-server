# Generated by Django 5.1.1 on 2024-11-07 16:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("route_api", "0002_alter_route_info"),
    ]

    operations = [
        migrations.AddField(
            model_name="route",
            name="end_name",
            field=models.CharField(max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="route",
            name="start_name",
            field=models.CharField(max_length=100, null=True),
        ),
    ]
