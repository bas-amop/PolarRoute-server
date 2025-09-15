from datetime import datetime
import logging

from celery.result import AsyncResult
from drf_spectacular.utils import extend_schema, inline_serializer
from jsonschema.exceptions import ValidationError
from meshiphi.mesh_generation.environment_mesh import EnvironmentMesh
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from rest_framework.reverse import reverse
from rest_framework import serializers

from polar_route.config_validation.config_validator import validate_vessel_config
from polarrouteserver.version import __version__ as polarrouteserver_version
from polarrouteserver.celery import app

from .models import Job, Vehicle, Route, Mesh
from .tasks import optimise_route
from .serializers import VehicleSerializer, VesselTypeSerializer, RouteSerializer
from .responses import (
    ResponseMixin,
    successResponseSchema,
    vehicleTypeListResponseSchema,
    routeAcceptedResponseSchema,
    routeStatusResponseSchema,
    recentRoutesResponseSchema,
    meshDetailResponseSchema,
    routeEvaluationResponseSchema,
    badRequestResponseSchema,
    notFoundResponseSchema,
    notAcceptableResponseSchema,
    noContentResponseSchema,
    acceptedResponseSchema,
    noMeshResponseSchema,
)
from .utils import (
    evaluate_route,
    route_exists,
    select_mesh,
    select_mesh_for_route_evaluation,
)

logger = logging.getLogger(__name__)


class LoggingMixin:
    """
    Provides full logging of requests and responses
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("django.request")

    def initial(self, request, *args, **kwargs):
        try:
            self.logger.debug(
                {
                    "request": request.data,
                    "method": request.method,
                    "endpoint": request.path,
                    "user": request.user.username,
                    "ip_address": request.META.get("REMOTE_ADDR"),
                    "user_agent": request.META.get("HTTP_USER_AGENT"),
                }
            )
        except Exception:
            self.logger.exception("Error logging request data")

        super().initial(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        try:
            self.logger.debug(
                {
                    "response": response.data,
                    "status_code": response.status_code,
                    "user": request.user.username,
                    "ip_address": request.META.get("REMOTE_ADDR"),
                    "user_agent": request.META.get("HTTP_USER_AGENT"),
                }
            )
        except Exception:
            self.logger.exception("Error logging response data")

        return super().finalize_response(request, response, *args, **kwargs)


class VehicleRequestView(LoggingMixin, ResponseMixin, GenericAPIView):
    serializer_class = VehicleSerializer

    @extend_schema(
        operation_id="api_vehicle_create_request",
        request=VehicleSerializer,
        responses={
            200: successResponseSchema,
            400: badRequestResponseSchema,
            406: notAcceptableResponseSchema,
        },
    )
    def post(self, request):
        """Entry point to create vehicles"""

        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}: {request.data}"
        )

        data = request.data

        # Using Polarroute's built in validation to validate vessel config supplied
        try:
            validate_vessel_config(data)
            logging.info("Vessel config is valid.")
        except Exception as e:
            if isinstance(e, ValidationError):
                error_message = f"Validation error: {e.message}"
            else:
                error_message = f"{e}"

            logging.error(error_message)

            return self.bad_request_response(error_message)

        # Separate out vessel_type and force_properties for checking logic below
        force_properties = data.get("force_properties", None)
        vessel_type = data["vessel_type"]

        # Check if vehicle exists already
        vehicle_queryset = Vehicle.objects.filter(vessel_type=vessel_type)

        # If the vehicle exists, obtain it and return an error if user has not specified force_properties
        if vehicle_queryset.exists():
            logger.info(f"Existing vehicle found: {vessel_type}")

            if not force_properties:
                return self.not_acceptable_response(
                    data,
                    "Pre-existing vehicle was found. "
                    "To force new properties on an existing vehicle, "
                    "include 'force_properties': true in POST request.",
                )

            # If a user has specified force_properties, update that vessel_type's properties
            # The vessel_type and force_properties fields need to be removed to allow updating
            vehicle_properties = data.copy()
            for key in ["vessel_type", "force_properties"]:
                vehicle_properties.pop(key, None)

            vehicle_queryset.update(**vehicle_properties)
            logger.info(f"Updating properties for existing vehicle: {vessel_type}")

            response_data = {"vessel_type": vessel_type}

        else:
            logger.info("Creating new vehicle:")

            # Create vehicle in database
            vehicle = Vehicle.objects.create(**data)

            # Prepare response data
            response_data = {"vessel_type": vehicle.vessel_type}

        return self.success_response(response_data)

    @extend_schema(
        operation_id="api_vehicle_list_retrieve",
        responses={
            200: successResponseSchema,
            204: noContentResponseSchema,
        },
    )
    def get(self, request):
        """Retrieve all vehicles"""

        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}"
        )

        logger.info("Fetching all vehicles")
        vehicles = Vehicle.objects.all()

        serializer = self.serializer_class(vehicles, many=True)

        return self.success_response(serializer.data)


class VehicleDetailView(LoggingMixin, ResponseMixin, GenericAPIView):
    serializer_class = VehicleSerializer

    @extend_schema(
        operation_id="api_vehicle_retrieve_by_type",
        responses={
            200: successResponseSchema,
            404: notFoundResponseSchema,
        },
    )
    def get(self, request, vessel_type):
        """Retrieve vehicle by vessel_type"""

        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}"
        )

        logger.info(f"Fetching vehicle(s) with vessel_type={vessel_type}")
        vehicles = Vehicle.objects.filter(vessel_type=vessel_type)

        serializer = self.serializer_class(vehicles, many=True)

        return self.success_response(serializer.data)

    @extend_schema(
        operation_id="api_vehicle_delete_by_type",
        responses={
            204: noContentResponseSchema,
            404: notFoundResponseSchema,
        },
    )
    def delete(self, request, vessel_type):
        """Delete vehicle by vessel_type"""

        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}"
        )

        try:
            vehicle = Vehicle.objects.get(vessel_type=vessel_type)
            vehicle.delete()
            logger.info(f"Deleted vehicle with vessel_type={vessel_type}")
            return self.no_content_response(
                data={"message": f"Vehicle '{vessel_type}' deleted successfully."}
            )
        except Vehicle.DoesNotExist:
            logger.error(
                f"Vehicle with vessel_type={vessel_type} not found for deletion."
            )
            return self.not_found_response(
                f"Vehicle with vessel_type '{vessel_type}' not found."
            )


class VehicleTypeListView(LoggingMixin, ResponseMixin, GenericAPIView):
    """
    Endpoint to list all distinct vessel_types available.
    """

    serializer_class = VesselTypeSerializer

    @extend_schema(
        operation_id="api_vehicle_available_list",
        responses={
            200: vehicleTypeListResponseSchema,
            204: noContentResponseSchema,
        },
    )
    def get(self, request):
        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}"
        )

        vessel_types = Vehicle.objects.values_list("vessel_type", flat=True).distinct()
        vessel_types_list = list(vessel_types)

        if not vessel_types_list:
            logger.warning("No available vessel_types found in the database.")
            return self.no_content_response(
                data={"vessel_types": []}, message="No available vessel types found."
            )

        logger.info(f"Returning {len(vessel_types_list)} distinct vessel_types")

        return self.success_response({"vessel_types": vessel_types_list})


class RouteRequestView(LoggingMixin, ResponseMixin, GenericAPIView):
    serializer_class = RouteSerializer

    @extend_schema(
        operation_id="api_route_create_request",
        request=inline_serializer(
            name="RouteCreationRequest",
            # This should be updated along with the json validation below
            fields={
                "start_lat": serializers.FloatField(
                    help_text="Starting latitude of the route."
                ),
                "start_lon": serializers.FloatField(
                    help_text="Starting longitude of the route."
                ),
                "end_lat": serializers.FloatField(
                    help_text="Ending latitude of the route."
                ),
                "end_lon": serializers.FloatField(
                    help_text="Ending longitude of the route."
                ),
                "start_name": serializers.CharField(
                    required=False,
                    allow_null=True,
                    help_text="Name of the start point.",
                ),
                "end_name": serializers.CharField(
                    required=False, allow_null=True, help_text="Name of the end point."
                ),
                "mesh_id": serializers.UUIDField(
                    required=False,
                    allow_null=True,
                    help_text="Optional: Custom mesh ID to use for route calculation.",
                ),
                "force_recalculate": serializers.BooleanField(
                    required=False,
                    default=False,
                    help_text="If true, forces recalculation even if an existing route is found.",
                ),
            },
        ),
        responses={
            202: routeAcceptedResponseSchema,
            400: badRequestResponseSchema,
            404: noMeshResponseSchema,
        },
    )
    def post(self, request):
        """Entry point for route requests"""

        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}: {request.data}"
        )

        data = request.data

        # TODO validate request JSON
        start_lat = data["start_lat"]
        start_lon = data["start_lon"]
        end_lat = data["end_lat"]
        end_lon = data["end_lon"]
        start_name = data.get("start_name", None)
        end_name = data.get("end_name", None)
        custom_mesh_id = data.get("mesh_id", None)
        force_recalculate = data.get("force_recalculate", False)

        if custom_mesh_id:
            try:
                logger.info(f"Got custom mesh id {custom_mesh_id} in request.")
                meshes = [Mesh.objects.get(id=custom_mesh_id)]
            except Mesh.DoesNotExist:
                msg = f"Mesh id {custom_mesh_id} requested. Does not exist."
                logger.info(msg)
                return self.not_found_response(msg)
        else:
            meshes = select_mesh(start_lat, start_lon, end_lat, end_lon)

        if meshes is None:
            return self.no_mesh_response()

        logger.debug(f"Using meshes: {[mesh.id for mesh in meshes]}")
        # TODO Future: calculate an up to date mesh if none available

        existing_route = route_exists(meshes, start_lat, start_lon, end_lat, end_lon)

        if existing_route is not None:
            if not force_recalculate:
                logger.info(f"Existing route found: {existing_route}")
                response_data = RouteSerializer(existing_route).data
                if existing_route.job_set.count() > 0:
                    existing_job = existing_route.job_set.latest("datetime")

                    response_data.update(
                        {
                            "info": {
                                "info": "Pre-existing route found and returned. To force new calculation, include 'force_recalculate': true in POST request."
                            },
                            "id": str(existing_job.id),
                            "status-url": reverse(
                                "route_detail",
                                args=[existing_job.id],
                                request=request,
                            ),
                            "polarrouteserver-version": polarrouteserver_version,
                        }
                    )

                else:
                    response_data.update(
                        {
                            "info": {
                                "error": "Pre-existing route was found but there was an error.\
                                To force new calculation, include 'force_recalculate': true in POST request."
                            }
                        }
                    )
                return self.accepted_response(response_data)
            else:
                logger.info(
                    f"Found existing route(s) but got force_recalculate={force_recalculate}, beginning recalculation."
                )

        logger.debug(
            f"Using mesh {meshes[0].id} as primary mesh with {[mesh.id for mesh in meshes[1:]]} as backup."
        )

        # Create route in database
        route = Route.objects.create(
            start_lat=start_lat,
            start_lon=start_lon,
            end_lat=end_lat,
            end_lon=end_lon,
            mesh=meshes[0],
            start_name=start_name,
            end_name=end_name,
        )

        # Start the task calculation
        task = optimise_route.delay(
            route.id, backup_mesh_ids=[mesh.id for mesh in meshes[1:]]
        )

        # Create database record representing the calculation job
        job = Job.objects.create(
            id=task.id,
            route=route,
        )

        # Prepare response data
        data = {
            "id": job.id,
            # url to request status of requested route
            "status-url": reverse("route_detail", args=[job.id], request=request),
            "polarrouteserver-version": polarrouteserver_version,
        }

        return self.accepted_response(data)


class RouteDetailView(LoggingMixin, ResponseMixin, GenericAPIView):
    serializer_class = RouteSerializer

    @extend_schema(
        operation_id="api_route_retrieve_status",
        responses={
            200: routeStatusResponseSchema,
            404: notFoundResponseSchema,
        },
    )
    def get(self, request, id):
        "Return status of route calculation and route itself if complete."

        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}"
        )

        # update job with latest state
        job = Job.objects.get(id=id)

        # status = job.status
        result = AsyncResult(id=str(id), app=app)
        status = result.state

        data = {
            "id": str(id),
            "status": status,
            "polarrouteserver-version": polarrouteserver_version,
        }

        data.update(RouteSerializer(job.route).data)

        if status == "FAILURE":
            data.update({"error": job.route.info})

        return self.success_response(data)

    @extend_schema(
        operation_id="api_route_cancel_job",
        responses={
            202: acceptedResponseSchema,
        },
    )
    def delete(self, request, id):
        """Cancel route calculation"""

        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}"
        )

        result = AsyncResult(id=str(id), app=app)
        result.revoke()

        return self.accepted_response({})


class RecentRoutesView(LoggingMixin, ResponseMixin, GenericAPIView):
    serializer_class = RouteSerializer

    @extend_schema(
        operation_id="api_recent_routes_list",
        responses={
            200: recentRoutesResponseSchema,
            204: noContentResponseSchema,
        },
    )
    def get(self, request):
        """Get recent routes"""

        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}"
        )

        # only get today's routes
        routes_today = Route.objects.filter(requested__date=datetime.now().date())
        response_data = []
        logger.debug(f"Found {len(routes_today)} routes today.")
        for route in routes_today:
            logger.debug(f"{route.id}")
            try:
                job = route.job_set.latest("datetime")
            except Job.DoesNotExist:
                logger.debug(f"Job does not exist for route {route.id}")
                continue

            result = AsyncResult(id=str(job.id), app=app)
            status = result.state

            data = {
                "id": str(job.id),
                "status": status,
                "polarrouteserver-version": polarrouteserver_version,
            }

            data.update(RouteSerializer(route).data)

            if status == "FAILURE":
                data.update({"error": route.info})

            response_data.append(data)

        return self.success_response(response_data)


class MeshView(LoggingMixin, ResponseMixin, APIView):
    serializer_class = None

    @extend_schema(
        operation_id="api_mesh_get",
        responses={
            200: meshDetailResponseSchema,
            404: noMeshResponseSchema,
        },
    )
    def get(self, request, id):
        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}"
        )

        data = {"polarrouteserver-version": polarrouteserver_version}

        try:
            mesh = Mesh.objects.get(id=id)
            data.update(
                dict(
                    id=mesh.id,
                    json=mesh.json,
                    geojson=EnvironmentMesh.load_from_json(mesh.json).to_geojson(),
                )
            )

            return self.success_response(data)

        except Mesh.DoesNotExist:
            return self.no_content_response(data)


class EvaluateRouteView(LoggingMixin, ResponseMixin, APIView):
    serializer_class = None

    @extend_schema(
        operation_id="api_route_evaluation",
        request=inline_serializer(
            name="RouteEvaluationRequest",
            fields={
                "route": serializers.JSONField(help_text="The route JSON to evaluate."),
                "custom_mesh_id": serializers.UUIDField(
                    required=False,
                    allow_null=True,
                    help_text="Optional: Custom mesh ID to use for evaluation.",
                ),
            },
        ),
        responses={
            200: routeEvaluationResponseSchema,
            404: noMeshResponseSchema,
        },
    )
    def post(self, request):
        data = request.data
        route_json = data.get("route", None)
        custom_mesh_id = data.get("custom_mesh_id", None)

        if custom_mesh_id:
            try:
                mesh = Mesh.objects.get(id=custom_mesh_id)
                meshes = [mesh]
            except Mesh.DoesNotExist:
                return self.no_mesh_response()
        else:
            meshes = select_mesh_for_route_evaluation(route_json)

            if meshes is None:
                return self.no_mesh_response()

        response_data = {"polarrouteserver-version": polarrouteserver_version}

        result_dict = evaluate_route(route_json, meshes[0])

        response_data.update(result_dict)

        return self.success_response(response_data)
