import time
import logging

from celery import shared_task

from .models import Route

logger = logging.getLogger(__name__)


@shared_task
def calculate_route(route_id: int):
    route = Route.objects.get(id=route_id)

    # dummy long-running process for initial development
    time.sleep(15)

    route_geojson = {"test": "Hello from Polar Route"}

    route.json = route_geojson

    # locate relevant mesh file
    # route calculation/optimisation using polar route
    # put route metadata in database
    # what to return? serialized Route object?

    return route_geojson
