from datetime import datetime
import logging

from celery.result import AsyncResult
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from jsonschema.exceptions import ValidationError
from meshiphi.mesh_generation.environment_mesh import EnvironmentMesh
import rest_framework.status
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import serializers

from polar_route.config_validation.config_validator import validate_vessel_config
from polarrouteserver.version import __version__ as polarrouteserver_version
from polarrouteserver.celery import app

from .models import Job, Vehicle, Route, Mesh
from .tasks import optimise_route
from .serializers import (
    VehicleSerializer,
    VesselTypeSerializer,
    RouteSerializer,
    JobSerializer,
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


class VehicleRequestView(LoggingMixin, GenericAPIView):
    serializer_class = VehicleSerializer

    @extend_schema(
        operation_id="api_vehicle_create_request",
        request=VehicleSerializer,
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="VehicleCreationSuccess",
                    fields={
                        "vessel_type": serializers.CharField(
                            help_text="The type of vessel successfully created or updated."
                        )
                    },
                ),
                description="Vehicle created or updated successfully.",
            ),
            400: OpenApiResponse(
                response=inline_serializer(
                    name="VehicleValidationError",
                    fields={
                        "info": serializers.DictField(
                            help_text="Details about the validation error, including the error message."
                        )
                    },
                ),
                description="Invalid input data for vehicle configuration.",
            ),
            406: OpenApiResponse(
                response=inline_serializer(
                    name="VehicleExistsError",
                    fields={
                        "info": serializers.DictField(
                            help_text="Details about the conflict, indicating a pre-existing vehicle."
                        )
                    },
                ),
                description="Pre-existing vehicle found, 'force_properties' not specified or not true.",
            ),
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

            return Response(
                data={**data, "info": {"error": {error_message}}},
                headers={"Content-Type": "application/json"},
                status=rest_framework.status.HTTP_400_BAD_REQUEST,
            )

        # Separate out vessel_type and force_properties for checking logic below
        force_properties = data.get("force_properties", None)
        vessel_type = data["vessel_type"]

        # Check if vehicle exists already
        vehicle_queryset = Vehicle.objects.filter(vessel_type=vessel_type)

        # If the vehicle exists, obtain it and return an error if user has not specified force_properties
        if vehicle_queryset.exists():
            logger.info(f"Existing vehicle found: {vessel_type}")

            if not force_properties:
                return Response(
                    data={
                        **data,
                        "info": {
                            "error": (
                                "Pre-existing vehicle was found. "
                                "To force new properties on an existing vehicle, "
                                "include 'force_properties': true in POST request."
                            )
                        },
                    },
                    headers={"Content-Type": "application/json"},
                    status=rest_framework.status.HTTP_406_NOT_ACCEPTABLE,
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

        return Response(
            response_data,
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="api_vehicle_list_retrieve",
        responses={
            200: OpenApiResponse(
                response=VehicleSerializer(many=True),
                description="List of all vehicles.",
            ),
            204: OpenApiResponse(
                response=None,
                description="No vehicles found.",
            ),
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

        return Response(
            serializer.data,
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_200_OK,
        )


class VehicleDetailView(LoggingMixin, GenericAPIView):
    serializer_class = VehicleSerializer

    @extend_schema(
        operation_id="api_vehicle_retrieve_by_type",
        responses={
            200: OpenApiResponse(
                response=VehicleSerializer(many=True),
                description="Vehicle details retrieved successfully.",
            ),
            404: OpenApiResponse(
                response=inline_serializer(
                    name="VehicleNotFound",
                    fields={
                        "error": serializers.CharField(
                            help_text="Error message indicating vehicle not found."
                        )
                    },
                ),
                description="Vehicle with the specified vessel_type not found.",
            ),
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

        return Response(
            serializer.data,
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="api_vehicle_delete_by_type",
        responses={
            204: OpenApiResponse(
                response=None, description="Vehicle deleted successfully."
            ),
            404: OpenApiResponse(
                response=inline_serializer(
                    name="VehicleDeleteNotFound",
                    fields={
                        "error": serializers.CharField(
                            help_text="Error message indicating vehicle not found."
                        )
                    },
                ),
                description="Vehicle with the specified vessel_type not found.",
            ),
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
            return Response(
                {"message": f"Vehicle '{vessel_type}' deleted successfully."},
                status=rest_framework.status.HTTP_204_NO_CONTENT,
            )
        except Vehicle.DoesNotExist:
            logger.error(
                f"Vehicle with vessel_type={vessel_type} not found for deletion."
            )
            return Response(
                {"error": f"Vehicle with vessel_type '{vessel_type}' not found."},
                status=rest_framework.status.HTTP_404_NOT_FOUND,
            )


class VehicleTypeListView(LoggingMixin, GenericAPIView):
    """
    Endpoint to list all distinct vessel_types available.
    """

    serializer_class = VesselTypeSerializer

    @extend_schema(
        operation_id="api_vehicle_available_list",
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="VesselTypeListSuccess",
                    fields={
                        "vessel_types": serializers.ListField(
                            child=serializers.CharField(),
                            help_text="List of available vessel types.",
                        ),
                    },
                ),
                description="List of available vessel types retrieved successfully.",
            ),
            204: OpenApiResponse(
                response=inline_serializer(
                    name="NoVesselTypesFound",
                    fields={
                        "vessel_types": serializers.ListField(
                            child=serializers.CharField(),
                            help_text="Empty list of vessel types.",
                        ),
                        "message": serializers.CharField(
                            help_text="Message indicating no vessel types were found."
                        ),
                    },
                ),
                description="No available vessel types found.",
            ),
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
            return Response(
                data={
                    "vessel_types": [],
                    "message": "No available vessel types found.",
                },
                headers={"Content-Type": "application/json"},
                status=rest_framework.status.HTTP_204_NO_CONTENT,
            )

        logger.info(f"Returning {len(vessel_types_list)} distinct vessel_types")

        return Response(
            data={"vessel_types": vessel_types_list},
            status=rest_framework.status.HTTP_200_OK,
            headers={"Content-Type": "application/json"},
        )


class RouteRequestView(LoggingMixin, GenericAPIView):
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
            202: OpenApiResponse(
                response=inline_serializer(
                    name="RouteRequestAccepted",
                    fields={
                        "job_id": serializers.UUIDField(
                            help_text="ID of the submitted job for route calculation."
                        ),
                        "status-url": serializers.URLField(
                            help_text="URL to check the status of the route calculation job."
                        ),
                        "polarrouteserver-version": serializers.CharField(
                            help_text="Version of PolarRoute-server."
                        ),
                        "info": serializers.DictField(
                            required=False,
                            help_text="Information or warning messages about the route calculation.",
                        ),
                    },
                ),
                description="Route calculation job submitted successfully.",
            ),
            400: OpenApiResponse(
                response=inline_serializer(
                    name="RouteCreationBadRequest",
                    fields={
                        "info": serializers.DictField(
                            help_text="Details about the error, e.g., missing parameters."
                        ),
                        "status": serializers.CharField(
                            help_text="Status of the request (e.g., FAILURE)."
                        ),
                    },
                ),
                description="Invalid request data.",
            ),
            200: OpenApiResponse(
                response=inline_serializer(
                    name="NoSuitableMesh",
                    fields={
                        "info": serializers.DictField(
                            help_text="Error message indicating no suitable mesh."
                        ),
                        "status": serializers.CharField(
                            help_text="Status of the request (e.g., FAILURE)."
                        ),
                    },
                ),
                description="No suitable mesh available for the requested route.",
            ),
        },
    )
    def post(self, request):
        """Entry point for route requests"""

        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}: {request.data}"
        )

        data = request.data

        # TODO validate request JSON
        try:
            start_lat = float(data["start_lat"])
            start_lon = float(data["start_lon"])
            end_lat = float(data["end_lat"])
            end_lon = float(data["end_lon"])
        except (ValueError, TypeError, KeyError) as e:
            msg = f"Invalid coordinate values provided: {e}"
            logger.error(msg)
            return Response(
                data={
                    "info": {"error": msg},
                    "status": "FAILURE",
                },
                headers={"Content-Type": "application/json"},
                status=rest_framework.status.HTTP_400_BAD_REQUEST,
            )

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
                return Response(
                    data={
                        "info": {"error": msg},
                        "status": "FAILURE",
                    },
                    headers={"Content-Type": "application/json"},
                    status=rest_framework.status.HTTP_202_ACCEPTED,
                )
        else:
            meshes = select_mesh(start_lat, start_lon, end_lat, end_lon)

        if meshes is None:
            return Response(
                data={
                    "info": {"error": "No suitable mesh available."},
                    "status": "FAILURE",
                },
                headers={"Content-Type": "application/json"},
                status=rest_framework.status.HTTP_200_OK,
            )

        logger.debug(f"Using meshes: {[mesh.id for mesh in meshes]}")
        # TODO Future: calculate an up to date mesh if none available

        existing_route = route_exists(meshes, start_lat, start_lon, end_lat, end_lon)

        if existing_route is not None:
            if not force_recalculate:
                logger.info(f"Existing route found: {existing_route}")

                # Check if there's an existing job for this route
                if existing_route.job_set.count() > 0:
                    existing_job = existing_route.job_set.latest("datetime")

                    response_data = {
                        "id": str(existing_job.id),
                        "status-url": reverse(
                            "job_detail", args=[existing_job.id], request=request
                        ),
                        "polarrouteserver-version": polarrouteserver_version,
                        "info": {
                            "message": "Pre-existing route found. Job already exists. To force new calculation, include 'force_recalculate': true in POST request."
                        },
                    }
                else:
                    # Route exists but no job - manual route insertion, job deletion without route etc
                    response_data = {
                        "info": {
                            "error": "Pre-existing route was found but there was an error with the job. To force new calculation, include 'force_recalculate': true in POST request."
                        }
                    }

                return Response(
                    data=response_data,
                    headers={"Content-Type": "application/json"},
                    status=rest_framework.status.HTTP_202_ACCEPTED,
                )
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
            "status-url": reverse("job_detail", args=[job.id], request=request),
            "polarrouteserver-version": polarrouteserver_version,
        }

        return Response(
            data,
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_202_ACCEPTED,
        )


class RouteDetailView(LoggingMixin, GenericAPIView):
    serializer_class = RouteSerializer

    @extend_schema(
        operation_id="api_route_retrieve_by_id",
        responses={
            200: OpenApiResponse(
                response=RouteSerializer,
                description="Route data retrieved successfully.",
            ),
            404: OpenApiResponse(
                response=inline_serializer(
                    name="RouteNotFound",
                    fields={
                        "error": serializers.CharField(
                            help_text="Error message indicating route not found."
                        )
                    },
                ),
                description="Route with the specified ID not found.",
            ),
        },
    )
    def get(self, request, id):
        """Return route data by route ID."""

        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}"
        )

        try:
            route = Route.objects.get(id=id)
        except Route.DoesNotExist:
            return Response(
                {"error": f"Route with id {id} not found."},
                headers={"Content-Type": "application/json"},
                status=rest_framework.status.HTTP_404_NOT_FOUND,
            )

        data = RouteSerializer(route).data
        data["polarrouteserver-version"] = polarrouteserver_version

        return Response(
            data,
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_200_OK,
        )


class RecentRoutesView(LoggingMixin, GenericAPIView):
    serializer_class = RouteSerializer

    @extend_schema(
        operation_id="api_recent_routes_list",
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="RecentRoutesSuccess",
                    fields={
                        "jobs": serializers.ListField(
                            child=inline_serializer(
                                name="JobWithRoute",
                                fields={
                                    "job_id": serializers.UUIDField(),
                                    "route_id": serializers.UUIDField(),
                                    "status": serializers.CharField(),
                                    "created": serializers.DateTimeField(),
                                    "start_lat": serializers.FloatField(),
                                    "start_lon": serializers.FloatField(),
                                    "end_lat": serializers.FloatField(),
                                    "end_lon": serializers.FloatField(),
                                    "start_name": serializers.CharField(
                                        allow_null=True
                                    ),
                                    "end_name": serializers.CharField(allow_null=True),
                                    "job_url": serializers.URLField(),
                                    "route_url": serializers.URLField(required=False),
                                    "info": serializers.DictField(required=False),
                                },
                            ),
                            help_text="List of recent jobs with associated route information.",
                        ),
                        "polarrouteserver-version": serializers.CharField(),
                    },
                ),
                description="List of recent routes with job information retrieved successfully.",
            ),
            204: OpenApiResponse(
                response=inline_serializer(
                    name="NoRecentRoutesFound",
                    fields={
                        "message": serializers.CharField(
                            help_text="Message indicating no recent routes were found."
                        ),
                    },
                ),
                description="No recent routes found for today.",
            ),
        },
    )
    def get(self, request):
        """Get recent routes"""

        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}"
        )

        # Get recent jobs instead of routes directly
        jobs_today = (
            Job.objects.filter(datetime__date=datetime.now().date())
            .select_related("route")
            .order_by("-datetime")
        )

        jobs_data = []
        logger.debug(f"Found {len(jobs_today)} jobs today.")

        for job in jobs_today:
            logger.debug(f"Processing job {job.id}")

            # Get current status from Celery
            result = AsyncResult(id=str(job.id), app=app)
            status = result.state

            job_data = {
                "job_id": job.id,
                "route_id": job.route.id,
                "status": status,
                "created": job.datetime.isoformat(),
                "start_lat": job.route.start_lat,
                "start_lon": job.route.start_lon,
                "end_lat": job.route.end_lat,
                "end_lon": job.route.end_lon,
                "start_name": job.route.start_name,
                "end_name": job.route.end_name,
                "job_url": reverse("job_detail", args=[job.id], request=request),
            }

            # Include route URL if job is successful
            if status == "SUCCESS":
                job_data["route_url"] = reverse(
                    "route_detail", args=[job.route.id], request=request
                )
                # Include route JSON data for backward compatibility with frontend
                route_data = RouteSerializer(job.route).data
                job_data.update(route_data)
            elif status == "FAILURE":
                job_data["info"] = {"error": job.route.info}

            jobs_data.append(job_data)

        response_data = {
            "jobs": jobs_data,
            "polarrouteserver-version": polarrouteserver_version,
        }

        return Response(
            response_data,
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_200_OK,
        )


class MeshView(LoggingMixin, APIView):
    serializer_class = None

    @extend_schema(
        operation_id="api_mesh_get",
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="MeshDetailSuccess",
                    fields={
                        "polarrouteserver-version": serializers.CharField(
                            help_text="Version of PolarRoute-server."
                        ),
                        "id": serializers.UUIDField(help_text="ID of the mesh."),
                        "json": serializers.JSONField(help_text="Mesh JSON."),
                        "geojson": serializers.JSONField(help_text="Mesh GeoJSON."),
                    },
                ),
                description="Mesh details retrieved successfully.",
            ),
            204: OpenApiResponse(
                response=inline_serializer(
                    name="MeshNotFound",
                    fields={
                        "polarrouteserver-version": serializers.CharField(
                            help_text="Version of PolarRoute-server."
                        )
                    },
                ),
                description="Mesh with the specified ID not found.",
            ),
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

            status = rest_framework.status.HTTP_200_OK

        except Mesh.DoesNotExist:
            status = rest_framework.status.HTTP_204_NO_CONTENT

        return Response(
            data,
            headers={"Content-Type": "application/json"},
            status=status,
        )


class EvaluateRouteView(LoggingMixin, APIView):
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
            200: OpenApiResponse(
                response=inline_serializer(
                    name="RouteEvaluationSuccess",
                    fields={
                        "polarrouteserver-version": serializers.CharField(
                            help_text="Version of PolarRoute-server."
                        ),
                        "evaluation_results": serializers.DictField(
                            help_text="Results of the route evaluation."
                        ),
                    },
                ),
                description="Route evaluated successfully.",
            ),
            204: OpenApiResponse(
                response=inline_serializer(
                    name="MeshNotFoundForEvaluation",
                    fields={
                        "error": serializers.CharField(
                            help_text="Error message indicating mesh not found."
                        )
                    },
                ),
                description="Mesh with the specified ID not found for evaluation.",
            ),
            400: OpenApiResponse(
                response=inline_serializer(
                    name="RouteEvaluationBadRequest",
                    fields={
                        "error": serializers.CharField(
                            help_text="Error message indicating invalid route data."
                        )
                    },
                ),
                description="Invalid route data provided for evaluation.",
            ),
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
                return Response(
                    {"error": f"Mesh with id {custom_mesh_id} not found."},
                    headers={"Content-Type": "application/json"},
                    status=rest_framework.status.HTTP_204_NO_CONTENT,
                )
        else:
            meshes = select_mesh_for_route_evaluation(route_json)

        response_data = {"polarrouteserver-version": polarrouteserver_version}

        result_dict = evaluate_route(route_json, meshes[0])

        response_data.update(result_dict)

        return Response(
            response_data,
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_200_OK,
        )


class JobView(LoggingMixin, GenericAPIView):
    """
    View for handling job status requests
    """

    serializer_class = JobSerializer

    @extend_schema(
        operation_id="api_job_retrieve_status",
        responses={
            200: OpenApiResponse(
                response=inline_serializer(
                    name="JobStatusSuccess",
                    fields={
                        "id": serializers.UUIDField(help_text="ID of the job."),
                        "status": serializers.CharField(
                            help_text="Current status of the job (PENDING, SUCCESS, FAILURE, etc.)."
                        ),
                        "polarrouteserver-version": serializers.CharField(
                            help_text="Version of PolarRoute-server."
                        ),
                        "route_id": serializers.UUIDField(
                            help_text="ID of the associated route."
                        ),
                        "created": serializers.DateTimeField(
                            help_text="When the job was created."
                        ),
                        "info": serializers.DictField(
                            required=False,
                            help_text="Additional information or error details if status is FAILURE.",
                        ),
                        "route_url": serializers.URLField(
                            required=False,
                            help_text="URL to retrieve the route data when status is SUCCESS.",
                        ),
                    },
                ),
                description="Job status retrieved successfully.",
            ),
            404: OpenApiResponse(
                response=inline_serializer(
                    name="JobNotFound",
                    fields={
                        "error": serializers.CharField(
                            help_text="Error message indicating job not found."
                        )
                    },
                ),
                description="Job with the specified ID not found.",
            ),
        },
    )
    def get(self, request, id):
        """Return status of job and route URL if complete."""

        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}"
        )

        try:
            job = Job.objects.get(id=id)
        except Job.DoesNotExist:
            return Response(
                {"error": f"Job with id {id} not found."},
                headers={"Content-Type": "application/json"},
                status=rest_framework.status.HTTP_404_NOT_FOUND,
            )

        # Get current status from Celery
        result = AsyncResult(id=str(id), app=app)
        status = result.state

        data = {
            "id": id,
            "status": status,
            "polarrouteserver-version": polarrouteserver_version,
            "route_id": job.route.id,
            "created": job.datetime.isoformat(),
        }

        if status == "SUCCESS":
            # Include route URL when job is complete
            data["route_url"] = reverse(
                "route_detail", args=[job.route.id], request=request
            )
        elif status == "FAILURE":
            data["info"] = {"error": job.route.info}

        return Response(
            data,
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_200_OK,
        )

    @extend_schema(
        operation_id="api_job_cancel",
        responses={
            202: OpenApiResponse(
                response=inline_serializer(
                    name="JobCancelAccepted",
                    fields={
                        "message": serializers.CharField(
                            help_text="Confirmation message that job cancellation was accepted."
                        )
                    },
                ),
                description="Job cancellation accepted.",
            ),
            404: OpenApiResponse(
                response=inline_serializer(
                    name="JobCancelNotFound",
                    fields={
                        "error": serializers.CharField(
                            help_text="Error message indicating job not found."
                        )
                    },
                ),
                description="Job with the specified ID not found.",
            ),
        },
    )
    def delete(self, request, id):
        """Cancel job"""

        logger.info(
            f"{request.method} {request.path} from {request.META.get('REMOTE_ADDR')}"
        )

        try:
            job = Job.objects.get(id=id)
        except Job.DoesNotExist:
            return Response(
                {"error": f"Job with id {id} not found."},
                headers={"Content-Type": "application/json"},
                status=rest_framework.status.HTTP_404_NOT_FOUND,
            )

        result = AsyncResult(id=str(id), app=app)
        result.revoke()

        return Response(
            {
                "message": f"Job {id} cancellation requested.",
                "job_id": str(job.id),
                "route_id": job.route.id,
            },
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_202_ACCEPTED,
        )
