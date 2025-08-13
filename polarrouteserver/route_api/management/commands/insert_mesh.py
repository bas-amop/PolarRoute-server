from datetime import datetime
import gzip
import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.utils import timezone

from polarrouteserver.route_api.models import EnvironmentMesh, VehicleMesh, Vehicle
from polarrouteserver.route_api.utils import calculate_json_md5


class Command(BaseCommand):
    help = "Manually insert a Mesh (or sequence of meshes) into the database.\n\
            Automatically detects whether each mesh is an EnvironmentMesh or VehicleMesh.\n\
            Takes json files or json files compressed gzip archives."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("meshes", nargs="+", type=str)

    def handle(self, *args: Any, **options: Any) -> str | None:
        for filepath in options["meshes"]:
            if filepath.endswith(".gz"):
                with gzip.open(filepath, "rb") as f:
                    mesh_json = json.load(f)
            else:
                with open(filepath, "r") as f:
                    mesh_json = json.load(f)

            # Calculate MD5 consistently with tasks.py
            md5 = calculate_json_md5(mesh_json)

            # Determine if this is a vehicle mesh or environment mesh
            is_vehicle_mesh = False
            vehicle_type = None

            config = mesh_json.get("config", {})

            # Look for vessel configuration in the mesh
            if "vessel_info" in config:
                is_vehicle_mesh = True
                vessel_config = config["vessel_info"]
                vehicle_type = vessel_config.get("vessel_type")
                self.stdout.write(f"Found vessel config with type: {vehicle_type}")

            mesh_type = "VehicleMesh" if is_vehicle_mesh else "EnvironmentMesh"
            self.stdout.write(f"Processing {mesh_type}: {filepath.split('/')[-1]}")

            # Create mesh entry based on type
            mesh_defaults = {
                "name": filepath.split("/")[-1],
                "valid_date_start": datetime.strptime(
                    mesh_json["config"]["mesh_info"]["region"]["start_time"],
                    "%Y-%m-%d",
                ),
                "valid_date_end": datetime.strptime(
                    mesh_json["config"]["mesh_info"]["region"]["end_time"],
                    "%Y-%m-%d",
                ),
                "created": timezone.now(),
                "json": mesh_json,
                "meshiphi_version": "manually_inserted",
                "lat_min": mesh_json["config"]["mesh_info"]["region"]["lat_min"],
                "lat_max": mesh_json["config"]["mesh_info"]["region"]["lat_max"],
                "lon_min": mesh_json["config"]["mesh_info"]["region"]["long_min"],
                "lon_max": mesh_json["config"]["mesh_info"]["region"]["long_max"],
            }

            if is_vehicle_mesh:
                if not vehicle_type:
                    raise CommandError(
                        "Vehicle mesh found but no vessel_type specified in config"
                    )

                # For vehicle meshes, we need to determine the vehicle type
                try:
                    vehicle = Vehicle.objects.get(vessel_type=vehicle_type)
                    self.stdout.write(
                        f"Found existing vehicle type '{vehicle_type}' in database"
                    )
                except Vehicle.DoesNotExist:
                    self.stdout.write(
                        f"Vehicle type '{vehicle_type}' not found in database, creating new vehicle"
                    )

                    # Get vessel config from either new or old format
                    vessel_config = config.get("vessel_info", {})

                    # Extract required fields from vessel config
                    max_speed = vessel_config.get("max_speed")
                    unit = vessel_config.get("unit")

                    if not max_speed or not unit:
                        raise CommandError(
                            f"Vehicle mesh missing required fields: max_speed={max_speed}, unit={unit}"
                        )

                    # Create new Vehicle from vessel config
                    vehicle_data = {
                        "vessel_type": vehicle_type,
                        "max_speed": max_speed,
                        "unit": unit,
                        "created": timezone.now(),
                    }

                    # Add optional fields if they exist in the vessel config
                    optional_fields = [
                        "max_ice_conc",
                        "min_depth",
                        "max_wave",
                        "excluded_zones",
                        "neighbour_splitting",
                        "beam",
                        "hull_type",
                        "force_limit",
                    ]

                    for field in optional_fields:
                        if field in vessel_config:
                            vehicle_data[field] = vessel_config[field]

                    try:
                        vehicle = Vehicle.objects.create(**vehicle_data)
                        self.stdout.write(
                            f"Created new vehicle '{vehicle_type}' in database"
                        )
                    except Exception as e:
                        raise CommandError(
                            f"Failed to create vehicle '{vehicle_type}': {e}"
                        )

                # Create VehicleMesh
                mesh_defaults["vehicle"] = vehicle
                mesh_defaults["environment_mesh"] = None

                mesh, created = VehicleMesh.objects.get_or_create(
                    md5=md5, defaults=mesh_defaults
                )
            else:
                # Create EnvironmentMesh
                mesh, created = EnvironmentMesh.objects.get_or_create(
                    md5=md5, defaults=mesh_defaults
                )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{mesh_type} inserted: name: {mesh.name} \nmd5: {mesh.md5} \
                            \nid: {mesh.id} \
                            \ncreated: {mesh.created} \
                            \nlat: {mesh.lat_min}:{mesh.lat_max}\
                            \nlon: {mesh.lon_min}:{mesh.lon_max}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.NOTICE(
                        f"{mesh_type} with md5: {mesh.md5} already in database. No new records created."
                    )
                )
