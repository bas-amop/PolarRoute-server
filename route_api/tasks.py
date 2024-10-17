from datetime import datetime
import gzip
import json
from pathlib import Path
import os

from celery import states
from celery.exceptions import Ignore
from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils import timezone
import numpy as np
import pandas as pd
import polar_route
from polar_route.route_planner import RoutePlanner
from polar_route.utils import extract_geojson_routes
import yaml

from polarrouteserver.celery import app
from .models import Mesh, Route


logger = get_task_logger(__name__)


@app.task(bind=True)
def optimise_route(
    self,
    route_id: int,
) -> dict:
    """
    Use PolarRoute to calculate optimal route from Route database object and mesh.
    Saves Route in database and returns route geojson as dictionary.

    Params:
        route_id(int): id of record in Route database table

    Returns:
        dict: route geojson as dictionary
    """
    route = Route.objects.get(id=route_id)
    mesh = route.mesh

    if mesh.created.date() < datetime.now().date():
        route.info = {
            "info": f"Latest available mesh from f{datetime.strftime(mesh.created, '%Y/%m/%d %H:%M%S')}"
        }

    # convert waypoints into pandas dataframe for PolarRoute
    waypoints = pd.DataFrame(
        {
            "Name": ["Start", "End"],
            "Lat": [route.start_lat, route.end_lat],
            "Long": [route.start_lon, route.end_lon],
            "Source": ["X", np.nan],
            "Destination": [np.nan, "X"],
        }
    )

    try:
        unsmoothed_routes = []
        route_planners = []
        for config in (settings.TRAVELTIME_CONFIG, settings.FUEL_CONFIG):
            rp = RoutePlanner(vessel_mesh, config, waypoints)

            # Calculate optimal dijkstra path between waypoints
            rp.compute_routes()

            route_planners.append(rp)

            # save the initial unsmoothed route
            logger.info(
                f"Saving unsmoothed Dijkstra paths for {config['objective_function']}-optimised route."
            )
            unsmoothed_routes.append(extract_geojson_routes(rp.to_json()))
            route.json_unsmoothed = unsmoothed_routes
            route.calculated = timezone.now()
            route.polar_route_version = polar_route.__version__
            route.save()

        smoothed_routes = []
        for i, rp in enumerate(route_planners):
            # Smooth the dijkstra routes
            rp.compute_smoothed_routes()
            # Save the smoothed route(s)
            logger.info(f"Route smoothing {i+1}/{len(route_planners)} complete.")
            smoothed_routes.append(extract_geojson_routes(rp.to_json()))

        # Update the database
        route.json = smoothed_routes
        route.calculated = timezone.now()
        route.polar_route_version = polar_route.__version__
        route.save()
        return smoothed_routes

    except Exception as e:
        logger.error(e)
        self.update_state(state=states.FAILURE)
        route.info = {"error": f"{e}"}
        route.save()
        raise Ignore()


@app.task(bind=True)
def import_new_meshes(self):
    """Look for new meshes and insert them into the database."""

    # find the latest metadata file
    files = os.listdir(settings.MESH_DIR)
    file_list = [
        os.path.join(settings.MESH_DIR, file)
        for file in files
        if file.startswith("upload_metadata_") and file.endswith(".yaml.gz")
    ]
    if len(file_list) == 0:
        msg = "Upload metadata file not found."
        logger.error(msg)
        raise FileNotFoundError(msg)
    latest_metadata_file = max(file_list, key=os.path.getctime)

    # load in the metadata
    with gzip.open(latest_metadata_file, "rb") as f:
        metadata = yaml.load(f.read(), Loader=yaml.Loader)

    meshes_added = []
    for record in metadata["records"]:
        # we only want the vessel json files
        if not record["filepath"].endswith(".vessel.json"):
            continue

        # extract the filename from the filepath
        mesh_filename = record["filepath"].split("/")[-1]

        # load in the mesh json
        with gzip.open(Path(settings.MESH_DIR, mesh_filename + ".gz"), "rb") as f:
            mesh_json = json.load(f)

        # create an entry in the database
        mesh, created = Mesh.objects.get_or_create(
            md5=record["md5"],
            defaults={
                "name": mesh_filename,
                "created": datetime.strptime(record["created"], "%Y%m%dT%H%M%S"),
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
