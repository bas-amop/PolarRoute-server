import logging

from celery.result import AsyncResult
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from polarrouteserver.celery import app
from route_api.models import Job, Route
from route_api.tasks import calculate_route

logger = logging.getLogger(__name__)


class RouteView(APIView):
    def get(self, request):
        """Entry point for route requests"""

        # check if route already exists, including if it has just been calculated in response to a previous request

        # if so, return route

        # else if route needs to be calculated
        task = calculate_route.delay("hello_world")

        _ = Job.objects.create(id=task.id)
        _ = Route.objects.create()

        data = {
            # url to request status of requested route
            "status-url": reverse("status", args=[task.id], request=request)
        }

        return Response(data)


class StatusView(APIView):
    def get(self, id, request):
        "Return status of route generation job"

        id = request.data["id"]

        res = AsyncResult(id, app=app)

        data = {"id": id, "status": res.state}

        # if route is ready, should return link to get route information, or return route?

        return Response(data)
