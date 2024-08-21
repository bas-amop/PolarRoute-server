from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from haversine import inverse_haversine, Unit, Direction
import pytest

from route_api.models import Route
from route_api.utils import route_exists

class TestRouteExists(TestCase):
    "Test function for checking for existing routes"

    def setUp(self):
        "Create a route in the test database"

        self.start_lat = 64.16
        self.start_lon = -21.99
        self.end_lat = 78.24
        self.end_lon = 15.61

        self.route = Route.objects.create(
            calculated=timezone.now(),
            start_lat=self.start_lat,
            start_lon=self.start_lon,
            end_lat=self.end_lat,
            end_lon=self.end_lon,
        )

    def test_route_exists(self):
        "Test case where exact requested route exists"

        route = route_exists(
            timezone.now(),
            start_lat=self.start_lat,
            start_lon=self.start_lon,
            end_lat=self.end_lat,
            end_lon=self.end_lon,
        )
        assert route == self.route

    def test_no_route_exists(self):
        "Test case where no similar route exists"

        route = route_exists(
            timezone.now(),
            start_lat=0,
            start_lon=0,
            end_lat=0,
            end_lon=0,
        )
        assert route is None

    def test_exact_route_returned(self):
        """Test exact route returned if other nearby routes exist"""

        # use inverse haversine method to create points at specified distance from start and end points
        in_tolerance_start = inverse_haversine(
            (self.start_lat, self.start_lon),
            0.9 * settings.WAYPOINT_DISTANCE_TOLERANCE,
            Direction.NORTH,
            unit=Unit.NAUTICAL_MILES,
        )
        in_tolerance_end = inverse_haversine(
            (self.end_lat, self.end_lon),
            0.9 * settings.WAYPOINT_DISTANCE_TOLERANCE,
            Direction.NORTH,
            unit=Unit.NAUTICAL_MILES,
        )

        # create another nearby route
        Route.objects.create(
            calculated=timezone.now(),
            start_lat=in_tolerance_start[0],
            start_lon=in_tolerance_start[1],
            end_lat=in_tolerance_end[0],
            end_lon=in_tolerance_end[1],
        )

        route = route_exists(
            timezone.now(),
            start_lat=self.start_lat,
            start_lon=self.start_lon,
            end_lat=self.end_lat,
            end_lon=self.end_lon,
        )
        assert route == self.route

        ### Test that closest of multiple routes is the one returned if no exact route is found
        # remove the exact route
        route.delete()

        in_tolerance_start = inverse_haversine(
            (self.start_lat, self.start_lon),
            0.8 * settings.WAYPOINT_DISTANCE_TOLERANCE,
            Direction.NORTH,
            unit=Unit.NAUTICAL_MILES,
        )
        in_tolerance_end = inverse_haversine(
            (self.end_lat, self.end_lon),
            0.8 * settings.WAYPOINT_DISTANCE_TOLERANCE,
            Direction.NORTH,
            unit=Unit.NAUTICAL_MILES,
        )

        # create another nearby route
        closest_route = Route.objects.create(
            calculated=timezone.now(),
            start_lat=in_tolerance_start[0],
            start_lon=in_tolerance_start[1],
            end_lat=in_tolerance_end[0],
            end_lon=in_tolerance_end[1],
        )

        # search for route with no exact match
        route = route_exists(
            timezone.now(),
            start_lat=self.start_lat,
            start_lon=self.start_lon,
            end_lat=self.end_lat,
            end_lon=self.end_lon,
        )
        assert route == closest_route
