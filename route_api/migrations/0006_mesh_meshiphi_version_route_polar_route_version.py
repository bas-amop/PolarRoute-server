# Generated by Django 5.0.7 on 2024-07-24 14:03

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "route_api",
            "0005_remove_job_status_route_json_alter_mesh_requested_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="mesh",
            name="meshiphi_version",
            field=models.CharField(max_length=60, null=True),
        ),
        migrations.AddField(
            model_name="route",
            name="polar_route_version",
            field=models.CharField(max_length=60, null=True),
        ),
    ]
