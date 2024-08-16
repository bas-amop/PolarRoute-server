import json
from pathlib import Path

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

from polarrouteserver.celery import app
from .models import Mesh, Route


logger = get_task_logger(__name__)


@app.task(bind=True)
def optimise_route(
    self,
    route_id: int,
    mesh: str | int = settings.MESH_PATH,
) -> dict:
    """
    Use PolarRoute to calculate optimal route from Route database object and mesh.
    Saves Route in database and returns route geojson as dictionary.

    Params:
        route_id(int): id of record in Route database table
        mesh(str|int): path to vessel mesh file or id of record in Mesh database table

    Returns:
        dict: route geojson as dictionary
    """
    route = Route.objects.get(id=route_id)

    if isinstance(mesh, Path | str):
        with open(mesh) as f:
            logger.info(f"Loading mesh file {mesh}")
            vessel_mesh = json.load(f)
    elif isinstance(mesh, int):
        logger.info(f"Loading mesh {mesh} from database.")
        vessel_mesh = Mesh.objects.get(id=mesh).json

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
            # Calculate traveltime optimised route
            rp = RoutePlanner(vessel_mesh, config, waypoints)

            # Calculate optimal dijkstra path between waypoints
            rp.compute_routes()

            route_planners.append(rp)

            # save the initial unsmoothed route
            logger.info(f"Saving unsmoothed Dijkstra paths for {config["objective_function"]}-optimised route.")
            unsmoothed_routes.append(extract_geojson_routes(rp.to_json()))
            route.json_unsmoothed = unsmoothed_routes
            route.calculated = timezone.now()
            route.polar_route_version = polar_route.__version__
            route.save()

        smoothed_routes = []
        for rp,i in enumerate(route_planners):
            # Smooth the dijkstra routes
            rp.compute_smoothed_routes()
            # Save the smoothed route(s)
            logger.info(f"Route smoothing {i}/{len(route_planners)} complete.")
            smoothed_routes.append(extract_geojson_routes(rp.to_json()))

        # Update the database
        route.json = smoothed_routes
        route.calculated = timezone.now()
        route.polar_route_version = polar_route.__version__
        route.save()
        return smoothed_routes

    except Exception as e:
        self.update_state(state=states.FAILURE)
        route.status = f"{e}"
        route.save()
        raise Ignore()


