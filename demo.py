"""Demo script for requesting routes from PolarRouteServer API using Python standard library."""

import argparse
import http.client
import json
import re
import sys
import time


class Location:
    def __init__(self, lat: float, lon: float):
        self.lat = lat
        self.lon = lon


STANDARD_LOCATIONS = {
    "bird": Location(-54.025, -38.044),
    "falklands": Location(-51.731, -57.706),
    "halley": Location(-75.059, -25.840),
    "rothera": Location(-67.764, -68.02),
    "kep": Location(-54.220, -36.433),
    "signy": Location(-60.720, -45.480),
    "nyalesund": Location(78.929, 11.928),
    "harwich": Location(51.949, 1.255),
    "rosyth": Location(56.017, -3.440),
}


def request_route(
    url: str,
    start: Location,
    end: Location,
    status_update_delay: int = 30,
    num_requests: int = 10,
) -> str:
    """Requests a route from polarRouteServer, repeating the request for status until the route is available.

    Args:
        url (str): _description_
        start (Location): _description_
        end (Location): _description_
        status_update_delay (int, optional): _description_. Defaults to 10.
        num_requests (int, optional): _description_. Defaults to 10.

    Raises:
        Exception: _description_

    Returns:
        str: _description_
    """

    # make route request
    print(f"Sending POST request to {url}/api/route")
    conn = http.client.HTTPConnection(url)
    conn.request(
        "POST",
        "/api/route",
        headers={"Host": url, "Content-Type": "application/json"},
        body=json.dumps(
            {
                "start": {
                    "latitude": start.lat,
                    "longitude": start.lon,
                },
                "end": {
                    "latitude": end.lat,
                    "longitude": end.lon,
                },
            }
        ),
    )
    response = conn.getresponse()

    print(f"{response.status} response, {response.reason}")
    if not str(response.status).startswith("2"):
        return None

    post_body = json.loads(response.read())
    # if route is returned
    if post_body.get("json") is not None:
        return post_body["json"]

    # if no route returned, request status at status-url
    status_url = post_body.get("status-url")
    if status_url is None:
        raise Exception("No status URL returned.")
    id = post_body.get("id")

    status_request_count = 0
    while status_request_count <= num_requests:
        status_request_count += 1
        print(
            f"Waiting for {status_update_delay} seconds before sending status request."
        )
        time.sleep(status_update_delay)

        print(
            f"Sending GET request {status_request_count}/{num_requests} to {url}/api/route/{id}"
        )
        # make route request
        conn = http.client.HTTPConnection(url)
        conn.request(
            "GET",
            f"/api/route/{id}",
            headers={"Host": url, "Content-Type": "application/json"},
        )
        response = conn.getresponse()

        get_body = json.loads(response.read())
        if get_body.get("status") == "PENDING":
            print("Route calculation PENDING. ")
            continue
        elif get_body.get("status") == "FAILURE":
            print("Route calculation FAILURE.")
            return None
        elif get_body.get("status") == "SUCCESS":
            print("Route calculation SUCCESS.")
            return get_body.get("json")
    print("Max number of requests sent. Quitting.")
    return None


def parse_location(location: str) -> tuple:
    """
    Takes a location either as the name of a standard location or latitude,longitude separated by a comma, e.g. -56.7,-65.01
    Returns a tuple of format (float, float) representing latitude and longitude coordinates of a location.
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
        help="Start location either as the name of a standard location or latitude,longitude separated by a comma, e.g. -56.7,-65.01",
        required=True,
    )
    parser.add_argument(
        "-e",
        "--end",
        type=str,
        nargs="?",
        help="End location either as the name of a standard location or latitude,longitude separated by a comma, e.g. -56.7,-65.01",
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
        "-f",
        "--force",
        action="store_true",
        help="Force polarRouteServer to recalculate the route even if it is already available.",
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


if __name__ == "__main__":
    args = parse_args()
    route = request_route(
        args.url,
        parse_location(args.start),
        parse_location(args.end),
        status_update_delay=args.delay,
    )

    if route is None:
        print(f"Got {route} returned. Quitting.")
        sys.exit(1)

    if args.output is not None:
        print(f"Writing out route reponse to {args.output}")
        args.output.write(json.dumps(route, indent=4))
    else:
        print(route)
