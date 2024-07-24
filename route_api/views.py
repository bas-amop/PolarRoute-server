import logging
import json

from django.http import HttpResponse

import celery.states
from celery.result import AsyncResult
from rest_framework.reverse import reverse
from rest_framework.generics import GenericAPIView

from polarrouteserver.celery import app
from route_api.models import Job, Route
from route_api.tasks import calculate_route

logger = logging.getLogger(__name__)


class RouteView(GenericAPIView):
    def post(self, request):
        """Entry point for route requests"""

        data = request.data

        # TODO validate request JSON
        start_lat = data["start"]["latitude"]
        start_lon = data["start"]["longitude"]
        end_lat = data["end"]["latitude"]
        end_lon = data["end"]["longitude"]

        # TODO check if route already exists, including if it has just been calculated in response to a previous request

        # if so, return route

        # else if route needs to be calculated

        # TODO Find the latest corresponding mesh object
        # TODO work out whether latest mesh contains start and end points
        # TODO calculate an up to date mesh if none available
        # mesh = Mesh.objects.get()

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
        )

        route.job = job
        route.save()

        # Prepare response data
        data = {
            # url to request status of requested route
            "status-url": reverse("status", args=[job.id], request=request)
        }

        return HttpResponse(
            json.dumps(data), headers={"Content-Type": "application/json"}
        )

    def delete(self, request):
        """Cancel route calculation"""

        id = request.data.get("id")

        result = AsyncResult(id=id, app=app)

        result.revoke()


class StatusView(GenericAPIView):
    def get(self, request, id):
        "Return status of route generation job"

        # update job with latest state
        job = Job.objects.get(id=id)

        status = job.status

        data = {"id": str(id), "status": status}

        if status is celery.states.SUCCESS:
            data.update({"route": job.route.json})

        return HttpResponse(
            json.dumps(data), headers={"Content-Type": "application/json"}
        )
