import json

from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils import timezone
import numpy as np
import pandas as pd
from polar_route.route_planner import RoutePlanner

from polarrouteserver.celery import app
from .models import Mesh, Route


logger = get_task_logger(__name__)


@app.task(bind=True)
def calculate_route(
    self,
    route_id: int,
    mesh: str | int = settings.MESH_PATH,
) -> dict:
    """
    Use PolarRoute to calculate route from Route database object and mesh.
    Saves Route in database and returns route geojson as dictionary.

    Params:
        route_id(int): id of record in Route database table
        mesh(str|int): path to vessel mesh file or id of record in Mesh database table

    Returns:
        dict: route geojson as dictionary
    """

    route = Route.objects.get(id=route_id)

    try:
        if isinstance(mesh, str):
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

        # Calculate route
        rp = RoutePlanner(vessel_mesh, settings.TRAVELTIME_CONFIG, waypoints)
        # Calculate optimal dijkstra path between waypoints
        rp.compute_routes()
        # Smooth the dijkstra routes
        rp.compute_smoothed_routes()

        route_mesh = rp.to_json()

        # Update the database
        route.json = route_mesh
        route.calculated = timezone.now()
        route.save()

        return route_mesh
    except Exception as e:
        logger.error(e)
        self.update_state(state="FAILURE")
