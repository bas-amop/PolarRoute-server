import json, subprocess, time, uuid
from unittest.mock import patch, PropertyMock

import celery.states
from celery.result import AsyncResult
from django.test import TestCase
import kombu.exceptions
from rest_framework.test import APIRequestFactory
import pytest

from polarrouteserver.celery import app
from route_api.views import RouteView
from route_api.models import Job, Route
from route_api.tasks import calculate_route


@pytest.mark.usefixtures("celery", "database")
class TestRouteRequest(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_request_route(self):
        data = {
            "start": {"latitude": 0.0, "longitude": 0.0},
            "end": {"latitude": 0.0, "longitude": 0.0},
        }

        request = self.factory.post("/api/route/", data=data, format="json")

        response = RouteView.as_view()(request)

        self.assertEqual(response.status_code, 202)

        assert f"api/route/{response.data.get('id')}" in response.data.get("status-url")
        assert isinstance(uuid.UUID(response.data.get("id")), uuid.UUID)


@pytest.mark.usefixtures("database")
class TestRouteStatus(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.route = Route.objects.create(
            start_lat=0.0, start_lon=0.0, end_lat=0.0, end_lon=0.0, mesh=None
        )

    def test_get_status_pending(self):
        self.job = Job.objects.create(
            id=uuid.uuid1(),
            route=self.route,
        )

        request = self.factory.get(f"/api/route/{self.job.id}")

        response = RouteView.as_view()(request, self.job.id)

        self.assertEqual(response.status_code, 200)

        assert response.data.get("status") == "PENDING"

    def test_get_status_complete(self):
        with patch(
            "route_api.models.Job.status", new_callable=PropertyMock
        ) as mock_job_status:
            mock_job_status.return_value = celery.states.SUCCESS

            self.job = Job.objects.create(
                id=uuid.uuid1(),
                route=self.route,
            )

            request = self.factory.get(f"/api/status/{self.job.id}")

            response = RouteView.as_view()(request, self.job.id)

            self.assertEqual(response.status_code, 200)

            assert response.data.get("status") == "SUCCESS"
            assert "json" in response.data.keys()
            # assert calculate_route.AsyncResult(id=self.job.id, app=app).state == "SUCCESS"
