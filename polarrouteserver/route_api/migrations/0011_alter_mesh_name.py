# Generated by Django 5.1.4 on 2024-12-19 10:34

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("route_api", "0010_alter_mesh_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mesh",
            name="name",
            field=models.CharField(max_length=150, null=True),
        ),
    ]
