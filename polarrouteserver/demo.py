"""Demo script for requesting routes from PolarRouteServer API using Python standard library."""

import argparse
import http.client
import json
import pprint
import re
import os
import ssl
import sys
import time
from urllib import request

os.environ["DJANGO_SETTINGS_MODULE"] = "polarrouteserver.settings.development"


class Location:
    def __init__(self, lat: float, lon: float, name: str = None):
        self.lat = lat
        self.lon = lon
        self.name = name


STANDARD_LOCATIONS = {
    "bird": Location(-54.025, -38.044, "bird"),
    "falklands": Location(-51.731, -57.706, "falklands"),
    "halley": Location(-75.059, -25.840, "halley"),
    "rothera": Location(-67.764, -68.02, "rothera"),
    "kep": Location(-54.220, -36.433, "kep"),
    "signy": Location(-60.720, -45.480, "signy"),
    "nyalesund": Location(78.929, 11.928, "nyalesund"),
    "harwich": Location(51.949, 1.255, "harwich"),
    "rosyth": Location(56.017, -3.440, "rosyth"),
}


def make_request(
    type: str, url: str, endpoint: str, headers: dict, body: dict = None
) -> http.client.HTTPResponse:
    """Sends HTTP request, prints details and returns response.

    Args:
        type (str): HTTP request type, e.g. "GET" or "POST"
        url (str): base url to send request to
        endpoint (str): endpoint, e.g. "/api/route/some-id"
        headers (dict): HTTP headers
        body (dict, optional): HTTP request body. Defaults to None.

    Returns:
        http.client.HTTPResponse
    """
    sending_str = f"Sending {type} request to {url}{endpoint}: \nHeaders: {headers}\n"

    if body:
        sending_str += f"Body: {body}\n"

    print(sending_str)

    # data = parse.urlencode(body).encode("utf-8") if body else None
    req = request.Request(url + endpoint, data=body, headers=headers)
    unverified_context = ssl._create_unverified_context()
    response = request.urlopen(req, context=unverified_context)

    print(f"Response: {response.status} {response.reason}")

    return json.loads(response.read()), response.status


def request_route(
    url: str,
    start: Location,
    end: Location,
    status_update_delay: int = 30,
    num_requests: int = 10,
    force_new_route: bool = False,
    mesh_id: int = None,
) -> str:
    """Requests a route from polarRouteServer, repeating the request for status until the route is available.

    Args:
        url (str): Base URL to send request to.
        start (Location): Start location of route
        end (Location): End location of route
        status_update_delay (int, optional): Delay in seconds between each status request. Defaults to 10.
        num_requests (int, optional): Max number of status requests before giving up. Defaults to 10.
        force_new_route (bool, optional): Force recalculation of an already existing route. Default: False.

    Raises:
        Exception: If no status URL is returned.

    Returns:
        str: JSON response of route request.
    """

    # make route request
    response_body, status = make_request(
        "POST",
        url,
        "/api/route",
        {"Content-Type": "application/json"},
        json.dumps(
            {
                "start_lat": start.lat,
                "start_lon": start.lon,
                "end_lat": end.lat,
                "end_lon": end.lon,
                "start_name": start.name,
                "end_name": end.name,
                "force_new_route": force_new_route,
                "mesh_id": mesh_id,
            },
        ).encode("utf-8"),
    )

    print(pprint.pprint(response_body))

    if not str(status).startswith("2"):
        return None

    # if route is returned
    if response_body.get("json") is not None:
        return response_body["json"]

    # if no route returned, request status at status-url
    status_url = response_body.get("status-url")
    if status_url is None:
        raise Exception("No status URL returned.")
    id = response_body.get("id")

    status_request_count = 0
    while status_request_count <= num_requests:
        status_request_count += 1
        print(
            f"\nWaiting for {status_update_delay} seconds before sending status request."
        )
        time.sleep(status_update_delay)

        # make route request
        print(f"Status request #{status_request_count} of {num_requests}")
        response_body, status = make_request(
            "GET",
            url,
            f"/api/route/{id}",
            headers={"Content-Type": "application/json"},
        )

        print(f"Route calculation {response_body.get('status')}.")
        print(pprint.pprint(response_body))
        if response_body.get("status") == "PENDING":
            continue
        elif response_body.get("status") == "FAILURE":
            return None
        elif response_body.get("status") == "SUCCESS":
            return response_body.get("json")
    print(
        f'Max number of requests sent. Quitting.\nTo send more status requests, run: "curl {url}/api/route/{id}"'
    )
    return None


def parse_location(location: str) -> Location:
    """
    Args:
     location (str): a location either as the name of a standard location or latitude,longitude separated by a comma, e.g. -56.7,-65.01

    Returns:
        a Location object
    """
    pattern = r"[+-]?([0-9]*[.])?[0-9]+,[+-]?([0-9]*[.])?[0-9]+"
    if location in STANDARD_LOCATIONS.keys():
        standard_location = STANDARD_LOCATIONS.get(location)
        return standard_location
    elif re.search(pattern, location):
        coords = re.search(pattern, location).group().split(",")
        return Location(float(coords[0]), float(coords[1]))
    else:
        raise ValueError(
            f"Expected input as the name of a standard location or latitude,longitude separated by a comma, e.g. -56.7,-65.01, got {location}"
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description=f"Requests a route from polarRouteServer, repeating the request for status until the route is available. \
        Specify start and end points by coordinates or from one of the standard locations: {[loc for loc in STANDARD_LOCATIONS.keys()]}"
    )
    parser.add_argument(
        "-u",
        "--url",
        type=str,
        nargs="?",
        default="localhost:8000",
        help="Base URL to send request to. Default: localhost:8000",
    )
    parser.add_argument(
        "-s",
        "--start",
        type=str,
        nargs="?",
        help="Start location either as the name of a standard location or latitude,longitude separated by a comma, e.g. -s-56.7,-65.01 Note that values starting with a minus (-) should use the single-letter form and omit the space.",
        required=True,
    )
    parser.add_argument(
        "-e",
        "--end",
        type=str,
        nargs="?",
        help="End location either as the name of a standard location or latitude,longitude separated by a comma, e.g. -e-56.7,-65.01 Note that values starting with a minus (-) should use the single-letter form and omit the space.",
        required=True,
    )
    parser.add_argument(
        "-d",
        "--delay",
        type=int,
        nargs="?",
        help="(integer) number of seconds to delay between status calls. Default: 30",
        default=30,
    )
    parser.add_argument(
        "-n",
        "--requests",
        type=int,
        nargs="?",
        help="(integer) number of status requests to make before stopping. Default: 10",
        default=30,
    )
    parser.add_argument(
        "-m",
        "--meshid",
        type=int,
        nargs="?",
        help="(integer) Custom mesh ID.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force polarRouteServer to create a new route even if one is already available.",
    )
    parser.add_argument(
        "-o",
        "--output",
        nargs="?",
        type=argparse.FileType("w"),
        default=None,
        help="File path to write out route to. (Default: None and print to stdout)",
    )

    return parser.parse_args()


def main():
    args = parse_args()
    route = request_route(
        args.url,
        parse_location(args.start),
        parse_location(args.end),
        status_update_delay=args.delay,
        force_new_route=args.force,
        mesh_id=args.meshid,
    )

    if route is None:
        print(f"Got {route} returned. Quitting.")
        sys.exit(1)

    if args.output is not None:
        print(f"Writing out route response to {args.output}")
        args.output.write(json.dumps(route, indent=4))
    else:
        print(route)


if __name__ == "__main__":
    main()
