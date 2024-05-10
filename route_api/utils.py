import datetime
import logging

from route_api.models import Route

logger = logging.getLogger(__name__)


def route_exists(
    date: datetime.date,
    waypoint_start_lat: float,
    waypoint_start_lon: float,
    waypoint_end_lat: float,
    waypoint_end_lon: float,
) -> Route:
    """Check if a route of given parameters has already been calculated.
    Return None if not and the route object if it has.
    """
    # TODO account for tolerance of waypoint location in linear distance
    # TODO check that route file exists, even if it has been previously calculated
    # TODO if multiple matching routes exist, which to return?

    routes = Route.objects.filter(
        calculated__date=date,
        waypoint_start_lat__exact=waypoint_start_lat,
        waypoint_start_lon__exact=waypoint_start_lon,
        waypoint_end_lat__exact=waypoint_end_lat,
        waypoint_end_lon__exact=waypoint_end_lon,
    )

    if len(routes) < 1:
        return None
    else:
        return routes.get()
