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
        # Calculate traveltime optimised route
        rp_traveltime = RoutePlanner(vessel_mesh, settings.TRAVELTIME_CONFIG, waypoints)

        # Calculate optimal dijkstra path between waypoints
        rp_traveltime.compute_routes()

        # save the initial unsmoothed route
        logger.info("Saving unsmoothed Dijkstra paths for traveltime-optimised route.")
        route.json_unsmoothed = extract_geojson_routes(rp_traveltime.to_json())
        route.calculated = timezone.now()
        route.polar_route_version = polar_route.__version__
        route.save()

        # Calculate fuel optimised route
        rp_fuel = RoutePlanner(vessel_mesh, settings.FUEL_CONFIG, waypoints)
        rp_fuel.compute_routes()
        logger.info("Saving unsmoothed Dijkstra paths for fuel-optimised route.")
        route.json_unsmoothed += extract_geojson_routes(rp_fuel.to_json())
        
        route.save()

        # Smooth the dijkstra routes
        rp_traveltime.compute_smoothed_routes()
        rp_fuel.compute_smoothed_routes()
        # Save the smoothed route(s)
        logger.info("Route smoothing complete.")
        traveltime_routes = extract_geojson_routes(rp_traveltime.to_json())
        fuel_routes = extract_geojson_routes(rp_fuel.to_json())
        extracted_routes = traveltime_routes + fuel_routes

        # Update the database
        route.json = extracted_routes
        route.calculated = timezone.now()
        route.polar_route_version = polar_route.__version__
        route.save()
        return extracted_routes

    except Exception as e:
        self.update_state(state=states.FAILURE)
        route.status = f"{e}"
        route.save()
        raise Ignore()

