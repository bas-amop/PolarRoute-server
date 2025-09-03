import json
import uuid
from unittest.mock import patch, PropertyMock

import celery.states
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIRequestFactory
import pytest

from polarrouteserver.route_api.views import (
    EvaluateRouteView,
    MeshView,
    VehicleRequestView,
    VehicleDetailView,
    VehicleTypeListView,
    RouteRequestView,
    RouteDetailView,
    RecentRoutesView,
    JobView,
)
from polarrouteserver.route_api.models import Job, Route
from .utils import add_test_mesh_to_db


class TestVehicleRequest(TestCase):
    """
    Test case for the Vehicle API endpoints. Covers:
    - Creating and updating vehicles
    - Validating input data for vehicles
    - Retrieving vehicle records
    - Deleting vehicle records
    """

    with open(settings.TEST_VEHICLE_PATH) as fp:
        vessel_config = json.load(fp)

    data = dict(vessel_config)

    def setUp(self):
        """
        Set up test environment for each test case, API request factory and test data.
        """
        self.factory = APIRequestFactory()
        self.data = self.__class__.data.copy()

    def post_vehicle(self, data):
        """
        Helper method to send a POST request to create or update a vehicle.

        Args:
            data (dict): The vehicle data payload.

        Returns:
            Response: Response object returned.
        """
        request = self.factory.post(
            "/api/vehicle", data=data, format="json"
        )
        return VehicleRequestView.as_view()(request)

    def test_create_update_vehicle(self):
        """
        Test creating a new vehicle, handling duplicates, and using force_properties.
        """
        data = self.data.copy()
        response = self.post_vehicle(data)
        self.assertEqual(response.status_code, 200)

        duplicate_response = self.post_vehicle(data)
        self.assertEqual(duplicate_response.status_code, 406)
        self.assertIn("info", duplicate_response.data)
        self.assertIn("error", duplicate_response.data["info"])
        self.assertIn(
            "Pre-existing vehicle was found.", duplicate_response.data["info"]["error"]
        )

        data.update({"force_properties": True})
        response_force = self.post_vehicle(data)
        self.assertEqual(response_force.status_code, 200)
        self.assertEqual(
            response.data.get("vessel_type"),
            response_force.data.get("vessel_type"),
        )

    def test_missing_property(self):
        """
        Test that omitting a required property (e.g., 'max_speed') results in validation error.
        """
        missing_property = self.data.copy()
        missing_property.pop("max_speed", None)
        response = self.post_vehicle(missing_property)

        self.assertEqual(response.status_code, 400)
        self.assertIn("info", response.data)
        self.assertIn("error", response.data["info"])
        self.assertIn(
            "Validation error: 'max_speed' is a required property",
            response.data["info"]["error"],
        )

    def test_wrong_type(self, data=data):
        """
        Test that submitting a wrong data type (e.g., string for 'max_speed') fails.
        """
        wrong_type = self.data.copy()
        wrong_type["max_speed"] = "really fast"
        response = self.post_vehicle(wrong_type)

        self.assertEqual(response.status_code, 400)
        self.assertIn("info", response.data)
        self.assertIn("error", response.data["info"])
        self.assertIn(
            "Validation error: 'really fast' is not of type 'number'",
            response.data["info"]["error"],
        )

    def test_type_error_on_invalid_input(self):
        """
        Test that submitting a non-dictionary raises a TypeError.
        """
        invalid_data = ["this", "is", "not", "a", "dict"]

        with self.assertRaises(TypeError):
            self.post_vehicle(invalid_data)

    def test_get_vehicle(self):
        """
        Test GET requests to fetch specific or all vehicles.
        """
        self.post_vehicle(self.data)

        # Test GET all vehicles
        request_all = self.factory.get("/api/vehicle")
        response_all = VehicleRequestView.as_view()(request_all)

        self.assertEqual(response_all.status_code, 200)
        self.assertTrue(len(response_all.data) >= 1)
        self.assertIn("vessel_type", response_all.data[0])

        # Test GET specific vehicle
        vessel_type = self.data["vessel_type"]
        request_specific = self.factory.get(f"/api/vehicle/{vessel_type}/")
        response_specific = VehicleDetailView.as_view()(
            request_specific, vessel_type=vessel_type
        )

        self.assertEqual(response_specific.status_code, 200)
        self.assertTrue(len(response_specific.data) >= 1)
        self.assertTrue(
            all(v["vessel_type"] == vessel_type for v in response_specific.data)
        )

    def test_delete_vehicle_success(self):
        """
        Test successful deletion of a vehicle.
        """
        self.post_vehicle(self.data)
        vessel_type = self.data["vessel_type"]

        request_delete = self.factory.delete(f"/api/vehicle/{vessel_type}/")
        response_delete = VehicleDetailView.as_view()(
            request_delete, vessel_type=vessel_type
        )

        self.assertEqual(response_delete.status_code, 204)
        self.assertIn("message", response_delete.data)

    def test_delete_vehicle_without_vessel_type(self):
        """
        Test deletion attempt without specifying a 'vessel_type' fails.
        We have intentionally not implemented this method.
        """
        request_delete = self.factory.delete("/api/vehicle/")
        response_delete = VehicleRequestView.as_view()(
            request_delete
        )

        self.assertEqual(response_delete.status_code, 405)

    def test_delete_vehicle_not_found(self):
        """
        Test deletion of a non-existent vehicle.
        """
        vessel_type = "non_existent_type"
        request_delete = self.factory.delete(f"/api/vehicle/{vessel_type}/")
        response_delete = VehicleDetailView.as_view()(
            request_delete, vessel_type=vessel_type
        )

        self.assertEqual(response_delete.status_code, 404)
        self.assertIn("error", response_delete.data)
        self.assertIn(vessel_type, response_delete.data["error"])


class TestVehicleTypeListView(TestCase):
    """
    Test case for the VehicleTypeListView endpoint at /api/vehicle/available, listing all available
    vehicles.
    """

    with open(settings.TEST_VEHICLE_PATH) as fp:
        vessel_config = json.load(fp)

    data = dict(vessel_config)

    def setUp(self):
        """
        Set up test environment for each test case, API request factory and test data.
        """
        self.factory = APIRequestFactory()
        self.data = self.__class__.data.copy()

    def post_vehicle(self, data):
        """
        Helper method to send a POST request to create or update a vehicle.

        Args:
            data (dict): The vehicle data.

        Returns:
            Response: Response object returned.
        """
        request = self.factory.post(
            "/api/vehicle", data=data, format="json"
        )
        return VehicleRequestView.as_view()(request)

    def test_get_vessel_types_empty(self):
        """
        Test the endpoint returns warning when no vehicles exist.
        """
        request = self.factory.get("/api/vehicle/available")
        response = VehicleTypeListView.as_view()(request)

        self.assertEqual(response.status_code, 204)
        self.assertIn("vessel_types", response.data)
        self.assertEqual(response.data["vessel_types"], [])
        self.assertIn("message", response.data)
        self.assertEqual(response.data["message"], "No available vessel types found.")

    def test_get_vessel_types_single_vehicle(self):
        """
        Test the endpoint after creating a single vehicle.
        """
        self.post_vehicle(self.data)

        request = self.factory.get("/api/vehicle/available")
        response = VehicleTypeListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("vessel_types", response.data)
        self.assertEqual(len(response.data["vessel_types"]), 1)
        self.assertIn(self.data["vessel_type"], response.data["vessel_types"])

    def test_get_vessel_types_multiple_vehicles(self):
        """
        Test the endpoint after creating vehicles with multiple distinct vessel_types.
        """
        data1 = self.data.copy()
        data2 = self.data.copy()
        data2["vessel_type"] = "Boaty McBoatface"

        self.post_vehicle(data1)
        self.post_vehicle(data2)

        request = self.factory.get("/api/vehicle/available")
        response = VehicleTypeListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("vessel_types", response.data)
        self.assertEqual(len(response.data["vessel_types"]), 2)
        self.assertCountEqual(
            response.data["vessel_types"],
            [data1["vessel_type"], data2["vessel_type"]],
        )


class TestRouteRequest(TestCase):
    def setUp(self):
        add_test_mesh_to_db()
        self.factory = APIRequestFactory()

    def test_custom_mesh_id(self):
        """Test that non-existent mesh id results in correct error message."""

        data = {
            "start_lat": 0.0,
            "start_lon": 0.0,
            "end_lat": 1.0,
            "end_lon": 1.0,
            "mesh_id": 999,
        }

        request = self.factory.post(
            "/api/route", data=data, format="json"
        )

        response = RouteRequestView.as_view()(request)

        self.assertEqual(response.status_code, 202)
        self.assertIn("Does not exist.", response.data["info"]["error"])

    def test_request_route(self):
        data = {
            "start_lat": 0.0,
            "start_lon": 0.0,
            "end_lat": 1.0,
            "end_lon": 1.0,
        }

        request = self.factory.post(
            "/api/route", data=data, format="json"
        )

        response = RouteRequestView.as_view()(request)

        self.assertEqual(response.status_code, 202)

        assert f"api/job/{response.data.get('id')}" in response.data.get("status-url")
        assert isinstance(uuid.UUID(response.data.get("id")), uuid.UUID)

        # Test that requesting the same route doesn't start a new job.
        # request the same route parameters
        request = self.factory.post(
            "/api/route", data=data, format="json"
        )
        response2 = RouteRequestView.as_view()(request)
        assert response.data.get("id") == response2.data.get("id")
        assert response.data.get("polarrouteserver-version") == response2.data.get(
            "polarrouteserver-version"
        )
        assert f"api/job/{response.data.get('id')}" in response2.data.get(
            "status-url"
        )

    def test_evaluate_route(self):
        with open(settings.TEST_ROUTE_PATH) as fp:
            route_json = json.load(fp)

        data = dict(route=route_json)

        request = self.factory.post(
            "/api/evaluate_route", data=data, format="json"
        )

        response = EvaluateRouteView.as_view()(request)
        self.assertEqual(response.status_code, 200)


pytestmark = pytest.mark.django_db


@pytest.mark.usefixtures("celery_app", "celery_worker", "celery_enable_logging")
@pytest.mark.django_db
class TestRouteStatus:

    pytestmark = pytest.mark.django_db

    def setUp(self):
        self.factory = APIRequestFactory()
        mesh = add_test_mesh_to_db()
        self.route = Route.objects.create(
            start_lat=1.1, start_lon=1.1, end_lat=2.0, end_lon=2.0, mesh=mesh
        )
        from polarrouteserver.route_api.tasks import optimise_route

        optimise_route(self.route.id)

    def test_get_status_pending(self):

        self.setUp()

        self.job = Job.objects.create(
            id=uuid.uuid1(),
            route=self.route,
        )

        request = self.factory.get(f"/api/job/{self.job.id}")

        response = JobView.as_view()(request, id=self.job.id)

        assert response.status_code == 200

        assert response.data.get("status") == "PENDING"

    def test_get_status_complete(self):

        self.setUp()

        with patch(
            "polarrouteserver.route_api.views.AsyncResult.state",
            new_callable=PropertyMock,
        ) as mock_job_status:
            mock_job_status.return_value = celery.states.SUCCESS

            self.job = Job.objects.create(
                id=uuid.uuid1(),
                route=self.route,
            )

            request = self.factory.get(f"/api/job/{self.job.id}")

            response = JobView.as_view()(request, id=self.job.id)

            assert response.status_code == 200
            assert response.data.get("status") == "SUCCESS"
            assert "route_url" in response.data

    def test_request_out_of_mesh(self):

        self.setUp()

        with open(settings.TEST_MESH_PATH) as f:
            mesh = json.load(f)

        # Request a point that is out of mesh
        lat_min = mesh["config"]["mesh_info"]["region"]["lat_min"]
        lat_max = mesh["config"]["mesh_info"]["region"]["lat_max"]
        lon_min = mesh["config"]["mesh_info"]["region"]["long_min"]
        lon_max = mesh["config"]["mesh_info"]["region"]["long_max"]

        data = {
            "start_lat": lat_min - 5,
            "start_lon": lon_min - 5,
            "end_lat": abs(lat_max - lat_min) / 2,
            "end_lon": abs(lon_max - lon_min) / 2,
        }

        # make route request
        request = self.factory.post(
            "/api/route", data=data, format="json"
        )

        # using try except to ignore deliberate error in celery task in test envrionment
        # in production, celery handles this
        try:
            post_response = RouteRequestView.as_view()(request)
        except AssertionError:
            pass

        assert post_response.status_code == 200
        assert post_response.data["info"]["error"] == "No suitable mesh available."

    def test_cancel_route(self):

        self.setUp()

        self.job = Job.objects.create(
            id=uuid.uuid1(),
            route=self.route,
        )

        request = self.factory.delete(f"/api/job/{self.job.id}")

        response = JobView.as_view()(request, id=self.job.id)

        assert response.status_code == 202
        
        # Test the response includes job and route info
        assert "message" in response.data
        assert "job_id" in response.data
        assert "route_id" in response.data
        assert str(self.job.id) in response.data["message"]
        assert response.data["job_id"] == str(self.job.id)
        assert response.data["route_id"] == self.route.id

    def test_cancel_nonexistent_job(self):
        """
        Test that attempting to cancel a non-existent job returns 404.
        """
        self.setUp()

        fake_job_id = uuid.uuid4()
        request = self.factory.delete(f"/api/job/{fake_job_id}")

        response = JobView.as_view()(request, id=fake_job_id)

        assert response.status_code == 404
        assert "error" in response.data
        assert str(fake_job_id) in response.data["error"]


class TestRouteDetailView(TestCase):
    """
    Test case for the RouteDetailView endpoint that returns route data by route ID.
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.mesh = add_test_mesh_to_db()
        
        # Create a test route with minimal data
        self.route = Route.objects.create(
            start_lat=60.0,
            start_lon=-1.0,
            end_lat=61.0,
            end_lon=-2.0,
            mesh=self.mesh,
            start_name="Test Start",
            end_name="Test End",
            json=None,
            json_unsmoothed=None,
            polar_route_version="0.2.0",
            info={"message": "Test route"}
        )

    def test_get_route_success(self):
        """
        Test successful retrieval of route data by ID.
        """
        request = self.factory.get(f"/api/route/{self.route.id}")
        response = RouteDetailView.as_view()(request, id=self.route.id)

        self.assertEqual(response.status_code, 200)
        
        # Check that route data is included
        self.assertEqual(response.data["start_lat"], 60.0)
        self.assertEqual(response.data["start_lon"], -1.0)
        self.assertEqual(response.data["end_lat"], 61.0)
        self.assertEqual(response.data["end_lon"], -2.0)
        self.assertEqual(response.data["start_name"], "Test Start")
        self.assertEqual(response.data["end_name"], "Test End")
        self.assertEqual(response.data["json"], [])
        self.assertEqual(response.data["json_unsmoothed"], None)
        self.assertEqual(response.data["polar_route_version"], "0.2.0")
        self.assertIn("error", response.data["info"])

    def test_get_route_not_found(self):
        """
        Test that requesting a non-existent route ID returns 404.
        """
        non_existent_id = 99999
        request = self.factory.get(f"/api/route/{non_existent_id}")
        response = RouteDetailView.as_view()(request, id=non_existent_id)

        self.assertEqual(response.status_code, 404)
        self.assertIn("error", response.data)
        self.assertIn(str(non_existent_id), response.data["error"])

    def test_get_route_with_minimal_data(self):
        """
        Test retrieval of route with minimal required data (no optional fields).
        """
        minimal_route = Route.objects.create(
            start_lat=50.0,
            start_lon=0.0,
            end_lat=51.0,
            end_lon=1.0,
            mesh=self.mesh
            # No optional fields like start_name, end_name, json, etc.
        )

        request = self.factory.get(f"/api/route/{minimal_route.id}")
        response = RouteDetailView.as_view()(request, id=minimal_route.id)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["start_lat"], 50.0)
        self.assertEqual(response.data["start_lon"], 0.0)
        self.assertEqual(response.data["end_lat"], 51.0)
        self.assertEqual(response.data["end_lon"], 1.0)
        self.assertIsNone(response.data.get("start_name"))
        self.assertIsNone(response.data.get("end_name"))


class TestGetRecentRoutesAndMesh(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.mesh = add_test_mesh_to_db()
        self.route1 = Route.objects.create(
            start_lat=0.0, start_lon=0.0, end_lat=0.0, end_lon=0.0, mesh=self.mesh
        )
        self.route2 = Route.objects.create(
            start_lat=1.0, start_lon=1.0, end_lat=1.0, end_lon=0.0, mesh=self.mesh
        )
        self.job1 = Job.objects.create(id=uuid.uuid1(), route=self.route1)
        self.job2 = Job.objects.create(id=uuid.uuid1(), route=self.route2)

    def test_recent_routes_request(self):

        request = self.factory.get(f"/api/recent_routes")

        response = RecentRoutesView.as_view()(request)

        assert response.status_code == 200
        assert len(response.data) == 2

    def test_mesh_get(self):

        request = self.factory.get(f"/api/mesh/{self.mesh.id}")

        response = MeshView.as_view()(request, self.mesh.id)

        assert response.status_code == 200
        assert response.data.get("json") is not None
        assert response.data.get("geojson") is not None
