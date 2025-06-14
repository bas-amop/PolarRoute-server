import hashlib
import json
import logging
import os
from tempfile import NamedTemporaryFile
from typing import Union

from django.conf import settings
import haversine
from polar_route.route_calc import route_calc
from polar_route.utils import convert_decimal_days

from .models import Mesh, Route

logger = logging.getLogger(__name__)


def select_mesh(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> Union[list[Mesh], None]:
    """Find the most suitable mesh from the database for a given set of start and end coordinates.
    Returns either a list of Mesh objects or None.
    """

    try:
        # get meshes which contain both start and end points
        containing_meshes = Mesh.objects.filter(
            lat_min__lte=start_lat,
            lat_max__gte=start_lat,
            lon_min__lte=start_lon,
            lon_max__gte=start_lon,
        ).filter(
            lat_min__lte=end_lat,
            lat_max__gte=end_lat,
            lon_min__lte=end_lon,
            lon_max__gte=end_lon,
        )

        # get the date of the most recently created mesh
        latest_date = containing_meshes.latest("created").created.date()

        # get all valid meshes from that creation date
        valid_meshes = containing_meshes.filter(created__date=latest_date)

        # return the smallest
        return sorted(valid_meshes, key=lambda mesh: mesh.size)

    except Mesh.DoesNotExist:
        return None


def route_exists(
    meshes: Union[Mesh, list[Mesh]],
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> Union[Route, None]:
    """Check if a route of given parameters has already been calculated.
    Works through list of meshes in order, returns first matching route
    Return None if not and the route object if it has.
    """

    if isinstance(meshes, Mesh):
        meshes = [meshes]

    for mesh in meshes:
        same_mesh_routes = Route.objects.filter(mesh=mesh)

        # use set to preserve uniqueness
        successful_route_ids = set()
        # remove any failed routes
        for route in same_mesh_routes:
            # job_set can't be filtered since status is a property method
            for job in route.job_set.all():
                if job.status != "FAILURE":
                    successful_route_ids.add(route.id)

        successful_routes = same_mesh_routes.filter(id__in=successful_route_ids)

        # if there are none return None
        if len(successful_routes) == 0:
            continue
        else:
            exact_routes = successful_routes.filter(
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
                    same_mesh_routes, start_lat, start_lon, end_lat, end_lon
                )
    return None


def _closest_route_in_tolerance(
    routes: list,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    tolerance_nm: float = settings.WAYPOINT_DISTANCE_TOLERANCE,
) -> Union[Route, None]:
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


def calculate_md5(filename):
    """create md5sum checksum for any file"""
    hash_md5 = hashlib.md5()

    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def evaluate_route(route_json: dict, mesh: Mesh) -> dict:
    """Run calculate_route method from PolarRoute to evaluate the fuel usage and travel time of a route.

    Args:
        route_json (dict): route to evaluate in geojson format.
        mesh (polarrouteserver.models.Mesh): mesh object on which to evaluate the route.

    Returns:
        dict: evaluated route
    """

    if route_json["features"][0].get("properties", None) is None:
        route_json["features"][0]["properties"] = {"from": "Start", "to": "End"}

    # route_calc only supports files, write out both route and mesh as temporary files
    route_file = NamedTemporaryFile(delete=False, suffix=".json")
    with open(route_file.name, "w") as fp:
        json.dump(route_json, fp)

    mesh_file = NamedTemporaryFile(delete=False, suffix=".json")
    with open(mesh_file.name, "w") as fp:
        json.dump(mesh.json, fp)

    try:
        calc_route = route_calc(route_file.name, mesh_file.name)
    except Exception as e:
        logger.error(e)
        return None
    finally:
        for file in (route_file, mesh_file):
            try:
                os.remove(file.name)
            except Exception as e:
                logger.warning(f"{file} not removed due to {e}")

    time_days = calc_route["features"][0]["properties"]["traveltime"][-1]
    time_str = convert_decimal_days(time_days)
    fuel = round(calc_route["features"][0]["properties"]["fuel"][-1], 2)

    return dict(
        route=calc_route, time_days=time_days, time_str=time_str, fuel_tonnes=fuel
    )


def select_mesh_for_route_evaluation(route: dict) -> Union[list[Mesh], None]:
    """Select a mesh from the database to be used for route evaluation.
    The latest mesh containing all points in the route will be chosen.
    If no suitable meshes are available, return None.

    Args:
        route (dict): GeoJSON route to be evaluated.

    Returns:
        Union[Mesh,None]: Selected mesh object or None.
    """

    coordinates = route["features"][0]["geometry"]["coordinates"]
    lats = [c[0] for c in coordinates]
    lons = [c[1] for c in coordinates]

    return select_mesh(min(lats), min(lons), max(lats), max(lons))


def check_mesh_data(mesh: Mesh) -> str:
    """Check a mesh object for missing data sources.

    Args:
        mesh (Mesh): mesh object to evaluate.

    Returns:
        A user-friendly warning message as a string.
    """

    message = ""

    mesh_data_sources = mesh.json["config"]["mesh_info"].get("data_sources", None)

    # check for completely absent data sources
    if mesh_data_sources is None:
        message = "Mesh has no data sources."
        return message

    expected_sources = settings.EXPECTED_MESH_DATA_SOURCES
    expected_num_data_files = settings.EXPECTED_MESH_DATA_FILES

    for data_type, data_loader in expected_sources.items():
        # check for missing individual data sources
        data_source = [d for d in mesh_data_sources if d["loader"] == data_loader]
        if len(data_source) == 0:
            message += f"No {data_type} data available for this mesh.\n"

            # skip to the next data source
            continue

        # check for unexpected number of data files
        data_source_num_expected_files = expected_num_data_files.get(data_loader, None)
        if data_source_num_expected_files is not None:
            actual_num_files = len(
                [f for f in data_source[0]["params"]["files"] if f != ""]
            )  # number of files removing empty strings
            if actual_num_files != data_source_num_expected_files:
                message += f"{actual_num_files} of expected {data_source_num_expected_files} days' data available for {data_type}.\n"

    return message
