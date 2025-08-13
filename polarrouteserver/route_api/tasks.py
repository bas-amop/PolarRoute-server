import copy
import datetime
import gzip
import json
from pathlib import Path
import tempfile
import os
import re

from celery import states
from celery.exceptions import Ignore
from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils import timezone
import numpy as np
import pandas as pd
import polar_route
from polar_route.route_planner.route_planner import RoutePlanner
from polar_route.utils import extract_geojson_routes
from polar_route.vessel_performance.vessel_performance_modeller import (
    VesselPerformanceModeller,
)
import yaml

from polarrouteserver.celery import app
from .models import Job, Route, VehicleMesh, EnvironmentMesh, Vehicle
from .utils import calculate_md5, check_mesh_data

VESSEL_MESH_FILENAME_PATTERN = re.compile(r"vessel_?.*\.json$")

logger = get_task_logger(__name__)


@app.task(bind=True)
def import_new_meshes(self):
    """Look for new meshes and insert them into the database."""

    if settings.MESH_METADATA_DIR is None:
        raise ValueError("MESH_METADATA_DIR has not been set.")

    # find the latest metadata file
    files = os.listdir(settings.MESH_METADATA_DIR)
    file_list = [
        os.path.join(settings.MESH_METADATA_DIR, file)
        for file in files
        if file.startswith("upload_metadata_") and file.endswith(".yaml.gz")
    ]
    if len(file_list) == 0:
        msg = "Upload metadata file not found."
        logger.error(msg)
        return
    latest_metadata_file = max(file_list, key=os.path.getctime)

    # load in the metadata
    logger.info(
        f"Loading metadata file from {os.path.join(settings.MESH_METADATA_DIR, latest_metadata_file)}"
    )
    with gzip.open(latest_metadata_file, "rb") as f:
        metadata = yaml.load(f.read(), Loader=yaml.Loader)

    meshes_added = []
    for record in metadata["records"]:
        # we only want the vessel json files
        if not bool(re.search(VESSEL_MESH_FILENAME_PATTERN, record["filepath"])):
            continue

        # extract the filename from the filepath
        mesh_filename = record["filepath"].split("/")[-1]

        # load in the mesh json
        try:
            zipped_filename = mesh_filename + ".gz"
            with gzip.open(
                Path(settings.MESH_DIR, zipped_filename), "rb"
            ) as gzipped_mesh:
                mesh_json = json.load(gzipped_mesh)
        except FileNotFoundError:
            logger.warning(f"{zipped_filename} not found. Skipping.")
            continue
        except PermissionError:
            logger.warning(
                f"Can't read {zipped_filename} due to permission error. File may still be transferring. Skipping."
            )
            continue

        # write out the unzipped mesh to temp file
        tfile = tempfile.NamedTemporaryFile(mode="w+", delete=True)
        json.dump(mesh_json, tfile, indent=4)
        tfile.flush()
        md5 = calculate_md5(tfile.name)

        # cross reference md5 hash from file record in metadata to actual file on disk
        if md5 != record["md5"]:
            logger.warning(
                f"Mesh file md5: {md5}\n\
                           does not match\n\
                           Metadata md5: {record['md5']}\n\
                           Skipping."
            )
            # if md5 hash from metadata file does not match that of the file itself,
            # there may have been a filename clash, skip this one.
            continue

        # create an entry in the database
        mesh, created = EnvironmentMesh.objects.get_or_create(
            md5=md5,
            defaults={
                "name": mesh_filename,
                "valid_date_start": datetime.datetime.strptime(
                    mesh_json["config"]["mesh_info"]["region"]["start_time"], "%Y-%m-%d"
                ).replace(tzinfo=datetime.timezone.utc),
                "valid_date_end": datetime.datetime.strptime(
                    mesh_json["config"]["mesh_info"]["region"]["end_time"], "%Y-%m-%d"
                ).replace(tzinfo=datetime.timezone.utc),
                "created": datetime.datetime.strptime(
                    record["created"], "%Y%m%dT%H%M%S"
                ).replace(tzinfo=datetime.timezone.utc),
                "json": mesh_json,
                "meshiphi_version": record["meshiphi"],
                "lat_min": record["latlong"]["latmin"],
                "lat_max": record["latlong"]["latmax"],
                "lon_min": record["latlong"]["lonmin"],
                "lon_max": record["latlong"]["lonmax"],
            },
        )
        if created:
            logger.info(
                f"Adding new mesh to database: {mesh.id} {mesh.name} {mesh.created}"
            )
            meshes_added.append(
                {"id": mesh.id, "md5": record["md5"], "name": mesh.name}
            )

    return meshes_added


def optimise_route(mesh_json: dict, route: Route) -> list:
    """
    Function to calculate optimal route using PolarRoute.

    Requires a VehicleMesh.

    Params:
        mesh_json: Vehicle mesh data as dictionary
        route: Route database object

    Returns:
        smoothed routes as list of geojson dictionaries
    """
    logger.info(f"Calculating route optimization for route {route.id}")

    # convert waypoints into pandas dataframe for PolarRoute
    waypoints = pd.DataFrame(
        {
            "Name": [
                "Start" if route.start_name is None else route.start_name,
                "End" if route.end_name is None else route.end_name,
            ],
            "Lat": [route.start_lat, route.end_lat],
            "Long": [route.start_lon, route.end_lon],
            "Source": ["X", np.nan],
            "Destination": [np.nan, "X"],
        }
    )

    unsmoothed_routes = []
    route_planners = []
    configs = (
        settings.TRAVELTIME_CONFIG,
        settings.FUEL_CONFIG,
    )

    for config in configs:
        rp = RoutePlanner(copy.deepcopy(mesh_json), config)

        # Calculate optimal dijkstra path between waypoints
        rp.compute_routes(waypoints)
        route_planners.append(rp)

        # save the initial unsmoothed route
        logger.info(
            f"Saving unsmoothed Dijkstra paths for {config['objective_function']}-optimised route."
        )
        if len(rp.routes_dijkstra) == 0:
            raise ValueError("Inaccessible. No routes found.")
        route_geojson = extract_geojson_routes(rp.to_json())
        route_geojson[0]["features"][0]["properties"]["objective_function"] = config[
            "objective_function"
        ]
        unsmoothed_routes.append(route_geojson)

    # Update route with unsmoothed data
    route.json_unsmoothed = unsmoothed_routes
    route.calculated = timezone.now()
    route.polar_route_version = polar_route.__version__
    route.save()

    smoothed_routes = []
    for i, rp in enumerate(route_planners):
        # Smooth the dijkstra routes
        rp.compute_smoothed_routes()
        # Save the smoothed route(s)
        logger.info(f"Route smoothing {i + 1}/{len(route_planners)} complete.")
        route_geojson = extract_geojson_routes(rp.to_json())
        route_geojson[0]["features"][0]["properties"]["objective_function"] = rp.config[
            "objective_function"
        ]
        smoothed_routes.append(route_geojson)

    # Update the database
    route.json = smoothed_routes
    route.calculated = timezone.now()
    route.polar_route_version = polar_route.__version__
    route.save()

    return smoothed_routes


def add_vehicle_to_environment_mesh(
    environment_mesh: EnvironmentMesh, vehicle: Vehicle
) -> VehicleMesh:
    """
    Non-task function to add vehicle performance data to an environment mesh,
    creating a new VehicleMesh.

    Params:
        environment_mesh: EnvironmentMesh database object
        vehicle: Vehicle database object

    Returns:
        newly created VehicleMesh database object
    """
    logger.info(
        f"Adding vehicle {vehicle.vessel_type} to environment mesh {environment_mesh.id}"
    )

    # Create vehicle config dictionary from Vehicle model
    vehicle_config = {
        "vessel_type": vehicle.vessel_type,
        "max_speed": vehicle.max_speed,
        "unit": vehicle.unit,
    }

    # Add optional vehicle properties if they exist
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
        value = getattr(vehicle, field, None)
        if value is not None:
            vehicle_config[field] = value

    try:
        # Use VesselPerformanceModeller to add vehicle performance to the mesh
        logger.info(f"Running vessel performance modelling for {vehicle.vessel_type}")

        # Initialize the vessel performance modeller
        vp = VesselPerformanceModeller(
            env_mesh_json=environment_mesh.json, vessel_config=vehicle_config
        )

        # Model accessibility (determines which cells are accessible to this vessel)
        vp.model_accessibility()

        # Model performance (calculates vessel-specific performance metrics)
        vp.model_performance()

        # Get the modified mesh with vessel performance data
        vessel_mesh_json = vp.to_json()

        logger.info(f"Vessel performance modelling completed for {vehicle.vessel_type}")

    except Exception as e:
        logger.error(f"Error during vessel performance modelling: {e}")
        raise RuntimeError(
            f"Failed to create vehicle mesh for {vehicle.vessel_type}: {e}"
        )

    # Calculate MD5 for the processed vessel mesh data
    vehicle_mesh_md5 = calculate_md5(json.dumps(vessel_mesh_json, sort_keys=True))

    # Create vehicle mesh by copying environment mesh metadata and updating with vessel data
    vehicle_mesh = VehicleMesh.objects.create(
        environment_mesh=environment_mesh,
        vehicle=vehicle,
        meshiphi_version=environment_mesh.meshiphi_version,
        md5=vehicle_mesh_md5,
        valid_date_start=environment_mesh.valid_date_start,
        valid_date_end=environment_mesh.valid_date_end,
        created=timezone.now(),
        lat_min=environment_mesh.lat_min,
        lat_max=environment_mesh.lat_max,
        lon_min=environment_mesh.lon_min,
        lon_max=environment_mesh.lon_max,
        name=f"{environment_mesh.name}_vehicle_{vehicle.vessel_type}",
        json=vessel_mesh_json,
    )

    logger.info(
        f"Created VehicleMesh {vehicle_mesh.id} for vehicle {vehicle.vessel_type}"
    )
    return vehicle_mesh


@app.task(bind=True)
def create_and_calculate_route(
    self,
    route_id: int,
    vehicle_type: str = None,
    backup_mesh_ids: list[int] = None,
) -> dict:
    """
    Calculate optimal route using a VehicleMesh.
    If needed, creates VehicleMesh from EnvironmentMesh + Vehicle.

    Params:
        route_id: id of record in Route database table
        vehicle_type: vessel type to use for route calculation (required for route calculation)
        backup_mesh_ids: list of database ids of backup meshes to try

    Returns:
        route geojson as dictionary
    """
    route = Route.objects.get(id=route_id)
    logger.info(f"Running route optimization for route {route.id}")

    # Routes MUST have a vehicle type to be calculated
    if not vehicle_type:
        raise ValueError("vehicle_type is required for route calculation")

    try:
        vehicle = Vehicle.objects.get(vessel_type=vehicle_type)
    except Vehicle.DoesNotExist:
        raise ValueError(f"Vehicle type '{vehicle_type}' not found in database")

    current_mesh = route.mesh

    # Check the type of mesh we have and handle accordingly
    if isinstance(current_mesh, VehicleMesh):
        # Check if it matches the requested vehicle type
        if current_mesh.vehicle == vehicle:
            logger.info(
                f"Using existing VehicleMesh {current_mesh.id} for vehicle {vehicle_type}"
            )
            vehicle_mesh = current_mesh
        else:
            # VehicleMesh exists but for wrong vehicle - get the EnvironmentMesh and create correct VehicleMesh
            logger.info(
                f"Current VehicleMesh {current_mesh.id} is for '{current_mesh.vehicle.vessel_type}' but '{vehicle_type}' was requested"
            )

            # Get the underlying EnvironmentMesh
            environment_mesh = current_mesh.environment_mesh

            # Create new VehicleMesh for this vehicle + environment combination
            logger.info(
                f"Creating new VehicleMesh for vehicle {vehicle_type} using EnvironmentMesh {environment_mesh.id}"
            )
            vehicle_mesh = add_vehicle_to_environment_mesh(environment_mesh, vehicle)

            # Update route to use the correct VehicleMesh
            route.mesh = vehicle_mesh
            route.save()

    elif isinstance(current_mesh, EnvironmentMesh):
        # Need to create VehicleMesh for the requested vehicle
        logger.info(
            f"Route has EnvironmentMesh {current_mesh.id}, creating VehicleMesh for vehicle {vehicle_type}"
        )

        # Create new VehicleMesh for this vehicle
        logger.info(
            f"Creating new VehicleMesh for vehicle {vehicle_type} using EnvironmentMesh {current_mesh.id}"
        )
        vehicle_mesh = add_vehicle_to_environment_mesh(current_mesh, vehicle)

        # Update route to use the VehicleMesh
        route.mesh = vehicle_mesh
        route.save()
    else:
        # Unknown mesh type
        raise ValueError(f"Unexpected mesh type: {type(current_mesh)}")

    # Now we have the correct VehicleMesh for route calculation
    mesh = vehicle_mesh

    # Add warning on mesh date if older than today
    if mesh.created.date() < datetime.datetime.now().date():
        route.info = {
            "info": f"Latest available mesh from {datetime.datetime.strftime(mesh.created, '%Y/%m/%d %H:%M%S')}"
        }

    data_warning_message = check_mesh_data(mesh)
    if data_warning_message != "":
        if route.info is None:
            route.info = {"info": data_warning_message}
        else:
            route.info["info"] = route.info["info"] + data_warning_message

    try:
        # Use the non-task function to calculate the route
        smoothed_routes = optimise_route(mesh.json, route)
        return smoothed_routes

    except Exception as e:
        logger.error(e)
        self.update_state(state=states.FAILURE)

        # Check if this is an inaccessible route error and we have backup meshes
        if "Inaccessible. No routes found" in str(e) and backup_mesh_ids:
            logger.info(
                f"No routes found on mesh {mesh.id}, trying with next mesh(es) {backup_mesh_ids}"
            )
            route.info = {"info": "Route inaccessible on mesh, trying next mesh."}

            try:
                backup_mesh_id = backup_mesh_ids[0]

                # Try to get backup mesh as VehicleMesh first
                try:
                    backup_vehicle_mesh = VehicleMesh.objects.get(id=backup_mesh_id)

                    # Check if this VehicleMesh is for the correct vehicle
                    if backup_vehicle_mesh.vehicle == vehicle:
                        logger.info(
                            f"Using backup VehicleMesh {backup_mesh_id} for vehicle {vehicle_type}"
                        )
                        route.mesh = backup_vehicle_mesh
                        route.save()
                    else:
                        # VehicleMesh exists but for wrong vehicle - get the EnvironmentMesh and create correct VehicleMesh
                        backup_environment_mesh = backup_vehicle_mesh.environment_mesh
                        if not backup_environment_mesh:
                            raise ValueError(
                                f"Backup VehicleMesh {backup_mesh_id} has no associated EnvironmentMesh"
                            )

                        # Check if correct VehicleMesh already exists
                        correct_vehicle_mesh = VehicleMesh.objects.filter(
                            vehicle=vehicle, environment_mesh=backup_environment_mesh
                        ).first()

                        if correct_vehicle_mesh:
                            logger.info(
                                f"Using existing VehicleMesh {correct_vehicle_mesh.id} for backup"
                            )
                            route.mesh = correct_vehicle_mesh
                            route.save()
                        else:
                            # Create new VehicleMesh for backup
                            logger.info(
                                f"Creating VehicleMesh for vehicle {vehicle_type} from backup EnvironmentMesh {backup_environment_mesh.id}"
                            )
                            new_vehicle_mesh = add_vehicle_to_environment_mesh(
                                backup_environment_mesh, vehicle
                            )
                            route.mesh = new_vehicle_mesh
                            route.save()

                except VehicleMesh.DoesNotExist:
                    # Try as EnvironmentMesh
                    try:
                        backup_environment_mesh = EnvironmentMesh.objects.get(
                            id=backup_mesh_id
                        )

                        # Check if VehicleMesh already exists for this combination
                        existing_vehicle_mesh = VehicleMesh.objects.filter(
                            vehicle=vehicle, environment_mesh=backup_environment_mesh
                        ).first()

                        if existing_vehicle_mesh:
                            logger.info(
                                f"Using existing VehicleMesh {existing_vehicle_mesh.id} for backup"
                            )
                            route.mesh = existing_vehicle_mesh
                            route.save()
                        else:
                            # Create VehicleMesh for backup EnvironmentMesh
                            logger.info(
                                f"Creating VehicleMesh for vehicle {vehicle_type} from backup EnvironmentMesh {backup_mesh_id}"
                            )
                            new_vehicle_mesh = add_vehicle_to_environment_mesh(
                                backup_environment_mesh, vehicle
                            )
                            route.mesh = new_vehicle_mesh
                            route.save()

                    except EnvironmentMesh.DoesNotExist:
                        raise ValueError(f"Backup mesh {backup_mesh_id} not found")

                # Retry with the backup mesh
                task = optimise_route.delay(route.id, vehicle_type, backup_mesh_ids[1:])
                _ = Job.objects.create(
                    id=task.id,
                    route=route,
                )
                raise Ignore()

            except (ValueError, RuntimeError) as backup_error:
                logger.error(
                    f"Error with backup mesh {backup_mesh_ids[0]}: {backup_error}"
                )
                route.info = {"error": "No accessible mesh found for route calculation"}
                route.save()
                raise e
        else:
            route.info = {"error": str(e)}
            route.save()
            raise Ignore()
