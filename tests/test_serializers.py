import json
import uuid
from datetime import datetime, timezone as dt_timezone
from unittest.mock import Mock, patch

from django.test import TestCase, RequestFactory
from django.utils import timezone

from polarrouteserver.route_api.models import Job, Route, VehicleMesh, Vehicle
from polarrouteserver.route_api.serializers import (
    RouteSerializer,
    JobStatusSerializer,
    VehicleSerializer,
)
from tests.utils import add_test_vehicle_mesh_to_db


class TestRouteSerializer(TestCase):
    """Test the RouteSerializer with various route data scenarios."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        # Create test mesh
        self.mesh = add_test_vehicle_mesh_to_db()

        # Sample route data with both optimisation types
        self.sample_route_data = [
            [{
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {
                        "objective_function": "traveltime",
                        "total_traveltime": 24.0
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[0, 0], [1, 1]]
                    }
                }]
            }],
            [{
                "type": "FeatureCollection", 
                "features": [{
                    "type": "Feature",
                    "properties": {
                        "objective_function": "fuel",
                        "total_fuel": 100.5,
                        "fuel_units": "kg"
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[0, 0], [1, 1]]
                    }
                }]
            }]
        ]

    def test_route_with_both_optimisation_types(self):
        """Test route serialization with both traveltime and fuel optimisation."""
        route = Route.objects.create(
            start_lat=-54.3,
            start_lon=-36.5,
            end_lat=-75.1,
            end_lon=-26.7,
            start_name="KEP",
            end_name="Halley",
            mesh=self.mesh,
            json=self.sample_route_data,
            json_unsmoothed=self.sample_route_data
        )

        serializer = RouteSerializer(route)
        data = serializer.data

        # Should return array of routes when multiple types available
        self.assertIn("routes", data)
        self.assertEqual(len(data["routes"]), 2)
        
        # Check both route types are present
        route_types = [r["type"] for r in data["routes"]]
        self.assertIn("traveltime", route_types)
        self.assertIn("fuel", route_types)
        
        # Check version is included
        self.assertIn("polarrouteserver-version", data)

    def test_route_with_single_optimisation_type(self):
        """Test route serialization with only one optimisation type."""
        single_route_data = [self.sample_route_data[0]]  # Only traveltime
        
        route = Route.objects.create(
            start_lat=-60.7,
            start_lon=-44.7,
            end_lat=-67.6,
            end_lon=-68.1,
            start_name="Bird",
            end_name="Rothera",
            mesh=self.mesh,
            json=single_route_data
        )

        serializer = RouteSerializer(route)
        data = serializer.data

        # Should return single route object when only one type
        self.assertNotIn("routes", data)
        self.assertEqual(data["type"], "traveltime")
        self.assertEqual(data["id"], str(route.id))
        self.assertIn("waypoints", data)
        self.assertIn("path", data)
        self.assertIn("optimisation", data)

    def test_route_with_no_route_data(self):
        """Test route serialization when no route data is available."""
        route = Route.objects.create(
            start_lat=-54.3,
            start_lon=-36.5,
            end_lat=-75.1,
            end_lon=-26.7,
            start_name="KEP",
            end_name="Halley",
            mesh=self.mesh,
            json=None
        )

        serializer = RouteSerializer(route)
        data = serializer.data

        # Should return error format
        self.assertEqual(data["type"], "error")
        self.assertEqual(data["id"], str(route.id))
        self.assertIn("info", data)
        self.assertEqual(data["info"]["error"], "No routes available for any optimisation type.")

    def test_route_waypoints_structure(self):
        """Test that route waypoints are structured correctly."""
        route = Route.objects.create(
            start_lat=-51.8,
            start_lon=-59.5,
            end_lat=-67.6,
            end_lon=-68.1,
            start_name="Falklands",
            end_name="Rothera",
            mesh=self.mesh,
            json=[self.sample_route_data[0]]
        )

        serializer = RouteSerializer(route)
        data = serializer.data

        waypoints = data["waypoints"]
        self.assertEqual(waypoints["start"]["lat"], -51.8)
        self.assertEqual(waypoints["start"]["lon"], -59.5)
        self.assertEqual(waypoints["start"]["name"], "Falklands")
        self.assertEqual(waypoints["end"]["lat"], -67.6)
        self.assertEqual(waypoints["end"]["lon"], -68.1)
        self.assertEqual(waypoints["end"]["name"], "Rothera")
        self.assertIn("path", data)

    def test_optimisation_metrics_traveltime(self):
        """Test traveltime optimisation metrics extraction."""
        route = Route.objects.create(
            start_lat=-60.7,
            start_lon=-45.6,
            end_lat=-67.6,
            end_lon=-68.1,
            start_name="Signy",
            end_name="Rothera",
            mesh=self.mesh,
            json=[self.sample_route_data[0]]
        )

        serializer = RouteSerializer(route)
        data = serializer.data

        metrics = data["optimisation"]["metrics"]
        self.assertIn("time", metrics)
        # Duration should be present as string
        self.assertEqual(metrics["time"]["duration"], "24.0")

    def test_optimisation_metrics_fuel(self):
        """Test fuel optimisation metrics extraction."""
        route = Route.objects.create(
            start_lat=-51.8,
            start_lon=-59.5,
            end_lat=-75.1,
            end_lon=-26.7,
            start_name="Falklands",
            end_name="Halley",
            mesh=self.mesh,
            json=[self.sample_route_data[1]]
        )

        serializer = RouteSerializer(route)
        data = serializer.data

        metrics = data["optimisation"]["metrics"]
        self.assertIn("fuelConsumption", metrics)
        self.assertEqual(metrics["fuelConsumption"]["value"], 100.5)
        self.assertEqual(metrics["fuelConsumption"]["units"], "kg")

    def test_optimisation_metrics_fuel_without_units(self):
        """Test fuel optimisation metrics with default units."""
        # Create test data without fuel_units
        fuel_data_no_units = [{
            "type": "FeatureCollection", 
            "features": [{
                "type": "Feature",
                "properties": {
                    "objective_function": "fuel",
                    "total_fuel": 75.2
                    # No fuel_units specified
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[0, 0], [1, 1]]
                }
            }]
        }]
        
        route = Route.objects.create(
            start_lat=-54.3,
            start_lon=-36.5,
            end_lat=-60.7,
            end_lon=-44.7,
            start_name="KEP",
            end_name="Bird",
            mesh=self.mesh,
            json=[fuel_data_no_units]
        )

        serializer = RouteSerializer(route)
        data = serializer.data

        metrics = data["optimisation"]["metrics"]
        self.assertIn("fuelConsumption", metrics)
        self.assertEqual(metrics["fuelConsumption"]["value"], 75.2)
        self.assertEqual(metrics["fuelConsumption"]["units"], "tons")  # Should default to "tons"

    def test_mesh_info_inclusion(self):
        """Test that mesh information is correctly included."""
        route = Route.objects.create(
            start_lat=-60.7,
            start_lon=-45.6,
            end_lat=-67.6,
            end_lon=-68.1,
            start_name="Signy",
            end_name="Rothera",
            mesh=self.mesh,
            json=[self.sample_route_data[0]]
        )

        serializer = RouteSerializer(route)
        data = serializer.data

        mesh_info = data["mesh"]
        self.assertEqual(mesh_info["id"], self.mesh.id)
        self.assertEqual(mesh_info["name"], "Test Mesh Vehicle")
        self.assertIn("bounds", mesh_info)
        self.assertEqual(mesh_info["bounds"]["latMin"], -50)
        self.assertEqual(mesh_info["bounds"]["latMax"], 50)

    def test_unsmoothed_route_fallback(self):
        """Test fallback to unsmoothed route when smoothed is not available."""
        # Only unsmoothed data available
        route = Route.objects.create(
            start_lat=-51.8,
            start_lon=-59.5,
            end_lat=-54.3,
            end_lon=-36.5,
            start_name="Falklands",
            end_name="KEP",
            mesh=self.mesh,
            json=None,  # No smoothed data
            json_unsmoothed=[self.sample_route_data[0]]
        )

        serializer = RouteSerializer(route)
        data = serializer.data

        # Should include warning about smoothing failure
        self.assertIn("info", data)
        self.assertIn("warning", data["info"])
        self.assertIn("Smoothing failed", data["info"]["warning"])


class TestJobStatusSerializer(TestCase):
    """Test the JobStatusSerializer with various job states."""

    def setUp(self):
        """Set up test data."""
        self.factory = RequestFactory()
        
        self.mesh = add_test_vehicle_mesh_to_db()

        self.route = Route.objects.create(
            start_lat=-60.7,
            start_lon=-44.7,
            end_lat=-75.1,
            end_lon=-26.7,
            start_name="Bird",
            end_name="Halley",
            mesh=self.mesh
        )

    @patch('polarrouteserver.route_api.serializers.AsyncResult')
    def test_job_status_success(self, mock_async_result):
        """Test job serialization when status is SUCCESS."""
        job = Job.objects.create(
            id=uuid.uuid4(),
            route=self.route
        )

        # Mock Celery result
        mock_result = Mock()
        mock_result.state = "SUCCESS"
        mock_async_result.return_value = mock_result

        request = self.factory.get('/api/job/')
        serializer = JobStatusSerializer(job, context={'request': request})
        data = serializer.data

        self.assertEqual(data["status"], "SUCCESS")
        self.assertEqual(data["route_id"], str(self.route.id))
        self.assertIn("route_url", data)
        self.assertIn("polarrouteserver-version", data)

    @patch('polarrouteserver.route_api.serializers.AsyncResult')
    def test_job_status_failure(self, mock_async_result):
        """Test job serialization when status is FAILURE."""
        job = Job.objects.create(
            id=uuid.uuid4(),
            route=self.route
        )

        # Add error info to route
        self.route.info = "Route calculation failed due to invalid coordinates"
        self.route.save()

        # Mock Celery result
        mock_result = Mock()
        mock_result.state = "FAILURE"
        mock_async_result.return_value = mock_result

        serializer = JobStatusSerializer(job)
        data = serializer.data

        self.assertEqual(data["status"], "FAILURE")
        self.assertIn("info", data)
        self.assertEqual(data["info"]["error"], "Route calculation failed due to invalid coordinates")

    @patch('polarrouteserver.route_api.serializers.AsyncResult')
    def test_job_status_pending(self, mock_async_result):
        """Test job serialization when status is PENDING."""
        job = Job.objects.create(
            id=uuid.uuid4(),
            route=self.route
        )

        # Mock Celery result
        mock_result = Mock()
        mock_result.state = "PENDING"
        mock_async_result.return_value = mock_result

        serializer = JobStatusSerializer(job)
        data = serializer.data

        self.assertEqual(data["status"], "PENDING")
        # Should not include route_url or info for pending jobs
        self.assertNotIn("route_url", data)
        self.assertNotIn("info", data)

    @patch('polarrouteserver.route_api.serializers.AsyncResult')
    def test_celery_result_caching(self, mock_async_result):
        """Test that AsyncResult objects are cached per serializer instance."""
        job = Job.objects.create(
            id=uuid.uuid4(),
            route=self.route
        )

        mock_result = Mock()
        mock_result.state = "SUCCESS"
        mock_async_result.return_value = mock_result

        serializer = JobStatusSerializer(job)
        
        # Call multiple methods that use Celery result
        status1 = serializer.get_status(job)
        status2 = serializer.get_status(job)
        route_url = serializer.get_route_url(job)

        # AsyncResult should only be created once
        self.assertEqual(mock_async_result.call_count, 1)
        self.assertEqual(status1, "SUCCESS")
        self.assertEqual(status2, "SUCCESS")


class TestVehicleSerializer(TestCase):
    """Test the VehicleSerializer."""

    def test_vehicle_serialization(self):
        """Test basic vehicle serialization."""
        vehicle = Vehicle.objects.create(
            vessel_type="test_vessel",
            max_speed=15.0,
            unit="knots",
            max_ice_conc=0.8,
            min_depth=10.0,
            beam=25.0,
            hull_type="slender"
        )

        serializer = VehicleSerializer(vehicle)
        data = serializer.data

        self.assertEqual(data["vessel_type"], "test_vessel")
        self.assertEqual(data["max_speed"], 15.0)
        self.assertEqual(data["unit"], "knots")
        self.assertEqual(data["max_ice_conc"], 0.8)
        self.assertEqual(data["min_depth"], 10.0)
        self.assertEqual(data["beam"], 25.0)
        self.assertEqual(data["hull_type"], "slender")
