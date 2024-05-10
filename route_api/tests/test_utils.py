from django.test import TestCase
from django.utils import timezone

from route_api.models import Route
from route_api.utils import route_exists


class TestRouteExists(TestCase):
    "Test function for checking for existing routes"

    def setUp(self):
        "Create a route in the test database"

        self.waypoint_start_lat = 64.16
        self.waypoint_start_lon = -21.99
        self.waypoint_end_lat = 78.24
        self.waypoint_end_lon = 15.61

        self.route = Route.objects.create(
            requested=timezone.now(),
            calculated=timezone.now(),
            waypoint_start_lat=self.waypoint_start_lat,
            waypoint_start_lon=self.waypoint_start_lon,
            waypoint_end_lat=self.waypoint_end_lat,
            waypoint_end_lon=self.waypoint_end_lon,
        )

    def test_route_exists(self):
        "Test case where exact requested route exists"

        route = route_exists(
            timezone.now(),
            waypoint_start_lat=self.waypoint_start_lat,
            waypoint_start_lon=self.waypoint_start_lon,
            waypoint_end_lat=self.waypoint_end_lat,
            waypoint_end_lon=self.waypoint_end_lon,
        )
        assert route == self.route

    def test_no_route_exists(self):
        "Test case where no similar route exists"

        route = route_exists(
            timezone.now(),
            waypoint_start_lat=0,
            waypoint_start_lon=0,
            waypoint_end_lat=0,
            waypoint_end_lon=0,
        )
        assert route is None
