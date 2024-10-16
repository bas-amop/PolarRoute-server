import datetime
import logging

from django.conf import settings
import haversine

from route_api.models import Mesh, Route

logger = logging.getLogger(__name__)


def select_mesh(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> Mesh | None:
    """Find the most suitable mesh from the database for a given set of start and end coordinates.
    Returns either a Mesh object or None.
    """

    try:
        return (
            Mesh.objects.filter(
                lat_min__lte=start_lat,
                lat_max__gte=start_lat,
                lon_min__lte=start_lon,
                lon_max__gte=start_lon,
            )
            .filter(
                lat_min__lte=end_lat,
                lat_max__gte=end_lat,
                lon_min__lte=end_lon,
                lon_max__gte=end_lon,
            )
            .latest("created")
        )
    except Mesh.DoesNotExist:
        return None


def route_exists(
    date: datetime.date,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> Route | None:
    """Check if a route of given parameters has already been calculated.
    Return None if not and the route object if it has.
    """

    # look for any routes already calculated from same day
    # as a proxy for "same data"
    # TODO check the mesh on this instead
    same_day_routes = Route.objects.filter(
        calculated__date=date,
    )

    # if there are none return None
    if len(same_day_routes) == 0:
        return None
    else:
        exact_routes = same_day_routes.filter(
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
        )

        if len(exact_routes) == 1:
            return exact_routes[0]
        elif len(exact_routes) > 1:
            # TODO if multiple matching routes exist, which to return?
            return exact_routes[0]
        else:
            # if no exact routes, look for any that are close enough
            return _closest_route_in_tolerance(
                same_day_routes, start_lat, start_lon, end_lat, end_lon
            )


def _closest_route_in_tolerance(
    routes: list,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    tolerance_nm: float = settings.WAYPOINT_DISTANCE_TOLERANCE,
) -> Route | None:
    """Takes a list of routes and returns the closest if any are within tolerance, or None."""

    def point_within_tolerance(point_1: tuple, point_2: tuple) -> bool:
        return haversine_distance(point_1, point_2) < tolerance_nm

    def haversine_distance(point_1: tuple, point_2: tuple) -> float:
        return haversine.haversine(point_1, point_2, unit=haversine.Unit.NAUTICAL_MILES)

    routes_in_tolerance = []
    for route in routes:
        if point_within_tolerance(
            (start_lat, start_lon), (route.start_lat, route.start_lon)
        ) and point_within_tolerance(
            (end_lat, end_lon), (route.end_lat, route.end_lon)
        ):
            routes_in_tolerance.append(
                {
                    "id": route.id,
                }
            )

    if len(routes_in_tolerance) == 0:
        return None
    elif len(routes_in_tolerance) == 1:
        return Route.objects.get(id=routes_in_tolerance[0]["id"])
    else:
        for i, route_dict in enumerate(routes_in_tolerance):
            route = Route.objects.get(id=route_dict["id"])
            routes_in_tolerance[i].update(
                {
                    "cumulative_distance": haversine_distance(
                        (start_lat, start_lon), (route.start_lat, route.start_lon)
                    )
                    + haversine_distance(
                        (end_lat, end_lon), (route.end_lat, route.end_lon)
                    )
                }
            )

        from operator import itemgetter

        closest_route = sorted(
            routes_in_tolerance, key=itemgetter("cumulative_distance")
        )[0]
        return Route.objects.get(id=closest_route["id"])
