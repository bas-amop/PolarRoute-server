import datetime
import os

import requests

__all__ = [
    "server_url",
    "request_route",
]

default_sic_date = datetime.date.today() - datetime.timedelta(days=1)


def server_url():
    return os.getenv("POLARROUTE_FRONTEND_INTERNAL_URL", "http://localhost:8000")


def request_route(
    url: str,
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    start_name: str = None,
    end_name: str = None,
    mesh_id: int = None,
    force_recalculate: bool = False,
) -> requests.Response:
    response = requests.post(
        url=url + "/api/route",
        data={
            "start_lat": float(start_lat),
            "start_lon": float(start_lon),
            "end_lat": float(end_lat),
            "end_lon": float(end_lon),
            "start_name": start_name,
            "end_name": end_name,
            "mesh_id": mesh_id,
            "force_recalculate": force_recalculate,
        },
    )

    return response


def get_route_geojson(route: dict):
    return route["json"][0][0]


def _summarise_route(route):
    keys_to_extract = [
        "id",
        "start_lat",
        "start_lon",
        "end_lat",
        "end_lon",
        "start_name",
        "end_name",
        "show",
        "mesh",
    ]
    return dict(filter(lambda item: item[0] in keys_to_extract, route.items()))


def _summarise_route_list(routes):
    summary = []
    for route in routes:
        summary.append(_summarise_route(route))
    return summary
