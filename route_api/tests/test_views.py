import  json, uuid
from unittest.mock import patch, PropertyMock

import celery.states
from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIRequestFactory
import pytest

from route_api.views import RouteView
from route_api.models import Job, Route

from route_api.tests.utils import add_test_mesh_to_db


class TestRouteRequest(TestCase):
    def setUp(self):
        add_test_mesh_to_db()
        self.factory = APIRequestFactory()

    def test_request_route(self):
        data = {
            "start": {"latitude": 0.0, "longitude": 0.0},
            "end": {"latitude": 1.0, "longitude": 1.0},
        }

        request = self.factory.post("/api/route/", data=data, format="json")

        response = RouteView.as_view()(request)

        self.assertEqual(response.status_code, 202)

        assert f"api/route/{response.data.get('id')}" in response.data.get("status-url")
        assert isinstance(uuid.UUID(response.data.get("id")), uuid.UUID)

    
        # Test that requesting the same route doesn't start a new job.
        # request the same route parameters
        request = self.factory.post("/api/route/", data=data, format="json")
        response2 = RouteView.as_view()(request)
        assert response.data.get('id') == response2.data.get('id')
        assert f"api/route/{response.data.get('id')}" in response2.data.get("status-url")


pytestmark = pytest.mark.django_db

@pytest.mark.usefixtures("celery_app","celery_worker", "celery_enable_logging")
@pytest.mark.django_db
class TestRouteStatus:
    
    pytestmark = pytest.mark.django_db

    def setUp(self):
        self.factory = APIRequestFactory()
        mesh=add_test_mesh_to_db()
        self.route = Route.objects.create(
            start_lat=0.0, start_lon=0.0, end_lat=0.0, end_lon=0.0, mesh=mesh
        )

    def test_get_status_pending(self):

        self.setUp()

        self.job = Job.objects.create(
            id=uuid.uuid1(),
            route=self.route,
        )

        request = self.factory.get(f"/api/route/{self.job.id}")

        response = RouteView.as_view()(request, self.job.id)

        assert response.status_code == 200

        assert response.data.get("status") == "PENDING"

    def test_get_status_complete(self):

        self.setUp()

        with patch(
            "route_api.views.AsyncResult.state", new_callable=PropertyMock
        ) as mock_job_status:
            mock_job_status.return_value = celery.states.SUCCESS

            self.job = Job.objects.create(
                id=uuid.uuid1(),
                route=self.route,
            )

            request = self.factory.get(f"/api/route/{self.job.id}")

            response = RouteView.as_view()(request, self.job.id)

            assert response.status_code == 200
            assert response.data.get("status") == "SUCCESS"
            assert "json_unsmoothed" in response.data.keys()
            assert "json" in response.data.keys()

    def test_request_out_of_mesh(self):

        self.setUp()
        
        with open(settings.MESH_PATH) as f:
            mesh = json.load(f)
        
        # Request a point that is out of mesh
        lat_min = mesh["config"]["mesh_info"]["region"]["lat_min"]
        lat_max = mesh["config"]["mesh_info"]["region"]["lat_max"]
        lon_min = mesh["config"]["mesh_info"]["region"]["long_min"]
        lon_max = mesh["config"]["mesh_info"]["region"]["long_max"]

        data = {
            "start": {"latitude": lat_min-5, "longitude": lon_min-5},
            "end": {"latitude": abs(lat_max-lat_min)/2, "longitude": abs(lon_max-lon_min)/2},
        }

        # make route request
        request = self.factory.post("/api/route/", data=data, format="json")

        # using try except to ignore deliberate error in celery task in test envrionment
        # in production, celery handles this
        try:
            post_response = RouteView.as_view()(request)
        except AssertionError:
            pass

        assert post_response.status_code == 204
        assert post_response.data["error"] == "No suitable mesh available."

    
    def test_cancel_route(self):

        self.setUp()

        self.job = Job.objects.create(
            id=uuid.uuid1(),
            route=self.route,
        )

        request = self.factory.delete(f"/api/route/{self.job.id}")

        response = RouteView.as_view()(request, self.job.id)

        assert response.status_code == 202
