import json
from pathlib import Path
import time
from unittest.mock import patch, PropertyMock

import celery.states
from celery.result import AsyncResult
from django.test import TestCase
import pytest

from polarrouteserver.celery import app
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
        """Calculate_route should return a dictionary"""
        route_json = calculate_route(self.route.id, self.test_mesh_path)
        assert isinstance(route_json, list)

    @pytest.mark.skip(reason="Requires production mesh file to be present, \
                      not suitable for automated testing.")
    def test_calculate_route_with_production_mesh(self):
        """Check using the default mesh"""
        route_json = calculate_route(self.route.id)
        assert isinstance(route_json, dict)

    def test_out_of_mesh_error(self):
        """Test that out of mesh locations causes error to be returned"""
        with open(self.test_mesh_path) as f:
            mesh = json.load(f)
        
        lat_min = mesh["config"]["mesh_info"]["region"]["lat_min"]
        lat_max = mesh["config"]["mesh_info"]["region"]["lat_max"]
        lon_min = mesh["config"]["mesh_info"]["region"]["long_min"]
        lon_max = mesh["config"]["mesh_info"]["region"]["long_max"]

        self.out_of_mesh_route = Route.objects.create(
            start_lat=lat_min-5, start_lon=lon_min-5,
            end_lat=abs(lat_max-lat_min)/2, end_lon=abs(lon_max-lon_min)/2,
            mesh=None
        )

        with pytest.raises(AssertionError):
            route_json = calculate_route(self.out_of_mesh_route.id)
        assert "error" in route_json.keys()

    def test_task_status(self):
        """Test that task object status is updated appropriately."""
        
        task = calculate_route.delay(self.route.id, self.test_mesh_path)
        assert AsyncResult(id = task.id, app=app).state == "PENDING"
        time.sleep(2)
        assert AsyncResult(id = task.id, app=app).state == "SUCCESS"


    def test_out_of_mesh_error_causes_task_failure(self):
        """Check that an example error (out of mesh) results in the task status being updated correctly."""
        with open(self.test_mesh_path) as f:
            mesh = json.load(f)
        
        lat_min = mesh["config"]["mesh_info"]["region"]["lat_min"]
        lat_max = mesh["config"]["mesh_info"]["region"]["lat_max"]
        lon_min = mesh["config"]["mesh_info"]["region"]["long_min"]
        lon_max = mesh["config"]["mesh_info"]["region"]["long_max"]

        self.out_of_mesh_route = Route.objects.create(
            start_lat=lat_min-5, start_lon=lon_min-5,
            end_lat=abs(lat_max-lat_min)/2, end_lon=abs(lon_max-lon_min)/2,
            mesh=None
        )

        task = calculate_route.delay(self.out_of_mesh_route.id)
        time.sleep(2)
        assert AsyncResult(id = task.id, app=app).state == "FAILURE"

# TODO test errors cause state update