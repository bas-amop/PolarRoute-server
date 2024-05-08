from celery.result import AsyncResult

from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from polarrouteserver.celery import app
from route_api.tasks import calculate_route

class Route(APIView):
    def get(self, request):
        """Entry point for route requests"""

        # check if route already exists

        # if so, return route

        # else if route needs to be calculated
        result = calculate_route.delay("hello_world")

        data = {
            'status-url': reverse('status', args=[result.id], request=request)
        }

        return Response(data)

class Status(APIView):
    def get(self, id, request):
        "Return status of route generation job"

        id = request.data['id']

        res = AsyncResult(id, app=app)

        data = {
            'id': id,
            'status': res.state
        }

        # if route is ready, should return link to get route information, or return route?

        return Response(data)
    