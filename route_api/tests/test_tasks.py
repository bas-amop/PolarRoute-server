from datetime import datetime, timedelta
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
from unittest.mock import patch, PropertyMock

from celery.exceptions import Ignore
from celery.result import AsyncResult
from django.conf import settings
from django.test import TestCase, TransactionTestCase
import pytest
import yaml

from polarrouteserver.celery import app
from route_api.models import Mesh, Route
from route_api.tasks import import_new_meshes, optimise_route
from route_api.tests.utils import add_test_mesh_to_db

class TestOptimiseRoute(TestCase):
    def setUp(self):
        self.start_point_name = "start point"
        self.end_point_name = "end point"
        self.mesh = add_test_mesh_to_db()
        self.route = Route.objects.create(
            start_lat=1.1, start_lon=1.1, end_lat=8.9, end_lon=8.9, mesh=self.mesh,
            start_name=self.start_point_name,
            end_name=self.end_point_name,
        )

    def test_optimise_route(self):
        """optimise_route should return a dictionary"""
        route_json = optimise_route(self.route.id)
        assert isinstance(route_json, list)
        assert route_json[0][0]["features"][0]["properties"]["from"] == self.start_point_name
        assert route_json[0][0]["features"][0]["properties"]["to"] == self.end_point_name

        route = Route.objects.get(id=self.route.id)
        assert route.json == route_json
        assert isinstance(route.json_unsmoothed, list)

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
            mesh=self.mesh
        )

        with pytest.raises(Ignore):
            optimise_route(self.out_of_mesh_route.id)

    def test_stale_mesh_warning(self):
        # make the created date on the mesh older than today for this test
        self.mesh.created = datetime.now().date() - timedelta(days=1)
        self.mesh.save()
        _ = optimise_route(self.route.id)
        route = Route.objects.get(id=self.route.id)
        assert "Latest available mesh from" in route.info["info"]

class TestTaskStatus(TransactionTestCase):

    def setUp(self):
        self.mesh = add_test_mesh_to_db()
        self.route = Route.objects.create(
            start_lat=1.1, start_lon=1.1, end_lat=8.9, end_lon=8.9, mesh=self.mesh
        )

    def test_task_status(self):
        """Test that task object status is updated appropriately."""

        task = optimise_route.delay(self.route.id)
        assert task.state == "SUCCESS"

    def test_unsmoothed_route_creation(self):
        """Test that route calculation task created unsmoothed route as well as the main route."""

        _ = optimise_route.delay(self.route.id)

        route = Route.objects.get(id=self.route.id)

        assert route.json is not None
        assert route.json_unsmoothed is not None


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
            mesh=self.mesh
        )

        with pytest.raises(AssertionError):
            task = optimise_route.delay(self.out_of_mesh_route.id)
            assert task.state == "FAILURE"

class TestImportNewMeshes(TestCase):

    def setUp(self):

        self.metadata_filename = "upload_metadata_test.yaml"
        self.metadata_filepath = Path(settings.MESH_DIR, self.metadata_filename)

        self.mesh_filenames = ["southern_test_mesh.vessel.json",
                               "central_test_mesh.vessel.json"]

        # create minimal test metadata file
        self.metadata = {
            "records": [
                {   
                    "filepath": str(Path(settings.MESH_DIR, self.mesh_filenames[0])),
                    "created": "20241016T154603",
                    "size": 123456,
                    "md5": hashlib.md5("dummy_hashable_string".encode('utf-8')).hexdigest(),
                    "meshiphi": "2.1.13",
                    "latlong": {
                        "latmin": -80.0,
                        "latmax": -40.0,
                        "lonmin":-110.0,
                        "lonmax":  -5.0,
                    }
                },
                {   
                    "filepath": str(Path(settings.MESH_DIR, self.mesh_filenames[1])),
                    "created": "20241016T155252",
                    "size": 123456,
                    "md5": hashlib.md5("dummy_hashable_string2".encode('utf-8')).hexdigest(),
                    "meshiphi": "2.1.13",
                    "latlong": {
                        "latmin": -60.0,
                        "latmax":  65.0,
                        "lonmin": -85.0,
                        "lonmax":  10.0,
                    }
                },
            ]
        }

        with open(self.metadata_filepath, 'w') as f:
            yaml.dump(self.metadata, f)

        with open(self.metadata_filepath, 'rb') as f_in:
            with gzip.open(Path(settings.MESH_DIR, self.metadata_filename+".gz"), 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

        for filename in self.mesh_filenames:
            with gzip.open(Path(settings.MESH_DIR, filename+".gz"), 'wb') as f:
                f.write(json.dumps({
                    "mesh": "dummy_data"
                }).encode('utf-8'))

    def tearDown(self):
        # cleanup files created for testing
        os.remove(Path(settings.MESH_DIR, self.metadata_filename))
        for filename in self.mesh_filenames + [self.metadata_filename]:
            os.remove(Path(settings.MESH_DIR, filename+".gz"))
        

    def test_import_new_meshes(self):
        
        meshes_added = import_new_meshes()

        for mesh in meshes_added:
            mesh_obj = Mesh.objects.get(id=mesh["id"])
            assert mesh_obj.id  == mesh["id"]
            assert mesh_obj.md5 == mesh["md5"]

        all_meshes = Mesh.objects.all()

        # run same meshes again and test not added again
        meshes_added = import_new_meshes()
        assert len(meshes_added) == 0

        all_meshes2 = Mesh.objects.all()
        assert list(all_meshes) == list(all_meshes2)
