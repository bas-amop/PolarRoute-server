from pathlib import Path

from django.test import TestCase

from route_api.models import Route
from route_api.tasks import calculate_route

test_mesh_path = str(Path("route_api", "tests", "fixtures", "test_vessel_mesh.json"))


class TestCalculateRoute(TestCase):
    def setUp(self):
        self.route = Route.objects.create(
            start_lat=1.1, start_lon=1.1, end_lat=8.9, end_lon=8.9, mesh=None
        )
        self.test_mesh_path = test_mesh_path

    def test_calculate_route(self):
        route_json = calculate_route(self.route.id, self.test_mesh_path)
        assert isinstance(route_json, dict)
