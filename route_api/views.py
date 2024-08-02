from datetime import datetime
import logging
import json

import celery.states
from celery.result import AsyncResult
import rest_framework.status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.reverse import reverse

from polarrouteserver.celery import app
from route_api.models import Job, Route
from route_api.tasks import calculate_route
from route_api.serializers import RouteSerializer
from route_api.utils import route_exists

logger = logging.getLogger(__name__)


class RouteView(GenericAPIView):
    serializer_class = RouteSerializer

    def post(self, request):
        """Entry point for route requests"""

        data = request.data

        # TODO validate request JSON
        start_lat = data["start"]["latitude"]
        start_lon = data["start"]["longitude"]
        end_lat = data["end"]["latitude"]
        end_lon = data["end"]["longitude"]

        existing_route = route_exists(
            datetime.today(), start_lat, start_lon, end_lat, end_lon
        )

        if existing_route is not None:
            return Response(
                RouteSerializer(existing_route),
                headers={"Content-Type": "application/json"},
                status=rest_framework.status.HTTP_200_OK,
            )

        # TODO Find the latest corresponding mesh object
        # TODO work out whether latest mesh contains start and end points
        # TODO calculate an up to date mesh if none available

        # Create route in database
        route = Route.objects.create(
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            mesh=None,
        )

        # Start the task calculation
        task = calculate_route.delay(route.id)

        # Create database record representing the calculation job
        job = Job.objects.create(
            id=task.id,
            route=route,
        )

        # Prepare response data
        data = {
            # url to request status of requested route
            "status-url": reverse("route", args=[job.id], request=request)
        }

        return Response(
            json.dumps(data),
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_202_ACCEPTED,
        )

    def get(self, request, id):
        "Return status of route calculation and route itself if complete."

        # update job with latest state
        job = Job.objects.get(id=id)

        status = job.status

        data = {"id": str(id), "status": status}

        data.update(RouteSerializer(job.route).data)

        if status is not celery.states.SUCCESS:
            # don't include the route json if it isn't available yet
            data.pop("json")
            data.pop("polar_route_version")

        return Response(
            json.dumps(data),
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_200_OK,
        )

    def delete(self, request):
        """Cancel route calculation"""

        id = request.data.get("id")

        result = AsyncResult(id=id, app=app)

        result.revoke()

        return Response(
            {},
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_202_ACCEPTED,
        )
