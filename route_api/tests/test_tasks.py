import json
from pathlib import Path
from unittest.mock import patch, PropertyMock

from celery.exceptions import Ignore
from celery.result import AsyncResult
from django.conf import settings
from django.test import TestCase, TransactionTestCase
import pytest

from polarrouteserver.celery import app
from route_api.models import Route
from route_api.tasks import optimise_route

class TestOptimiseRoute(TestCase):
    def setUp(self):
        self.route = Route.objects.create(
            start_lat=1.1, start_lon=1.1, end_lat=8.9, end_lon=8.9, mesh=None
        )

    def test_optimise_route(self):
        """optimise_route should return a dictionary"""
        route_json = optimise_route(self.route.id)
        assert isinstance(route_json, list)

    def test_out_of_mesh_error(self):
        """Test that out of mesh locations causes error to be returned"""
        with open(settings.MESH_PATH) as f:
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

        with pytest.raises(Ignore):
            optimise_route(self.out_of_mesh_route.id)

class TestTaskStatus(TransactionTestCase):

    def setUp(self):
        self.route = Route.objects.create(
            start_lat=1.1, start_lon=1.1, end_lat=8.9, end_lon=8.9, mesh=None
        )

    def test_task_status(self):
        """Test that task object status is updated appropriately."""

        task = optimise_route.delay(self.route.id)
        assert task.state == "SUCCESS"


    def test_out_of_mesh_error_causes_task_failure(self):
        """Check that an example error (out of mesh) results in the task status being updated correctly."""
        with open(settings.MESH_PATH) as f:
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
            task = optimise_route.delay(self.out_of_mesh_route.id)
            assert task.state == "FAILURE"
