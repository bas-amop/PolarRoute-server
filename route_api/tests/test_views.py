import json

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from route_api.views import RouteView


class TestRouteView(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

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


class TestStatusView(TestCase):
    def setUp(self):
        pass

    def test_get_status(self):
        pass
