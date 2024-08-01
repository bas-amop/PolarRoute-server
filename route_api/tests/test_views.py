import json, subprocess, time, uuid
from unittest.mock import patch, PropertyMock

import celery.states
from django.test import TestCase
import kombu.exceptions
from rest_framework.test import APIRequestFactory

from polarrouteserver.celery import app
from route_api.views import RouteView, StatusView
from route_api.models import Job, Route


class CeleryTestCase(TestCase):
    def setUp(self):
        # start up the celery worker and rabbitmq container
        subprocess.run(["make", "start-celery"])
        # wait for celery worker to start up
        while True:
            try:
                if app.control.inspect().active() is not None:
                    break
            except kombu.exceptions.OperationalError:
                time.sleep(1)
                continue

    def tearDown(self):
        subprocess.run(["make", "stop-rabbitmq", "stop-celery"])


class TestRouteView(CeleryTestCase):
    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()

    def tearDown(self):
        super().tearDown()

    def test_request_route(self):
        data = {
            "start": {"latitude": 0.0, "longitude": 0.0},
            "end": {"latitude": 0.0, "longitude": 0.0},
        }

        request = self.factory.post("/api/route/", data=data, format="json")

        response = RouteView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        response_content = json.loads(response.content.decode())
        assert response_content.get("status-url") is not None


class TestStatusView(CeleryTestCase):
    def setUp(self):
        super().setUp()
        self.factory = APIRequestFactory()
        self.route = Route.objects.create(
            start_lat=0.0, start_lon=0.0, end_lat=0.0, end_lon=0.0, mesh=None
        )

    def tearDown(self):
        super().tearDown()

    def test_get_status_pending(self):
        self.job = Job.objects.create(
            id=uuid.uuid1()
        )
        self.route.job=self.job

        request = self.factory.get(f"/api/status/{self.job.id}")

        response = StatusView.as_view()(request, self.job.id)

        self.assertEqual(response.status_code, 200)

        response_content = json.loads(response.content.decode())
        assert response_content.get("status") == "PENDING"

    def test_get_status_complete(self):
        with patch(
            "route_api.models.Job.status", new_callable=PropertyMock
        ) as mock_job_status:
            mock_job_status.return_value = celery.states.SUCCESS

            self.job = Job.objects.create(
                id=uuid.uuid1(),
            )
            self.route.job=self.job
            self.route.save()

            request = self.factory.get(f"/api/status/{self.job.id}")

            response = StatusView.as_view()(request, self.job.id)

            self.assertEqual(response.status_code, 200)

            response_content = json.loads(response.content.decode())
            assert response_content.get("status") == "SUCCESS"
            assert "route" in response_content.keys()
