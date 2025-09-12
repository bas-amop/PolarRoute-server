from drf_spectacular.utils import OpenApiResponse, inline_serializer
from rest_framework.response import Response
from rest_framework import serializers
import rest_framework.status

from .serializers import VehicleSerializer


class ResponseMixin:
    """
    Mixin providing standardized API response methods that integrate with OpenAPI schema.

    This mixin ensures consistent response formatting across all API endpoints and
    provides response methods that correspond to the standardized schema objects
    defined in this module.

    Usage:
        class MyView(ResponseMixin, APIView):
            def get(self, request):
                return self.success_response({"data": "example"})

    Schema Integration:
        Each method in this mixin corresponds to a schema object:
        - success_response() -> successResponseSchema (200)
        - bad_request_response() -> badRequestResponseSchema (400) - for validation and input errors
        - not_found_response() -> notFoundResponseSchema (404)
        - not_acceptable_response() -> notAcceptableResponseSchema (406) - for resource conflicts
        - no_content_response() -> noContentResponseSchema (204)
        - accepted_response() -> acceptedResponseSchema (202)
        - no_mesh_response() -> noMeshResponseSchema (404)
    """

    def no_mesh_response(self):
        """
        Return standardized response for when no mesh is available.
        Corresponds to: noMeshResponseSchema (404)
        """
        return Response(
            data={
                "info": {"error": "No mesh available."},
                "status": "FAILURE",
            },
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_404_NOT_FOUND,
        )

    def success_response(self, data, status_code=rest_framework.status.HTTP_200_OK):
        """
        Return standardized success response.
        Corresponds to: successResponseSchema (200)
        """
        return Response(
            data,
            headers={"Content-Type": "application/json"},
            status=status_code,
        )

    def bad_request_response(
        self, error_message, status_code=rest_framework.status.HTTP_400_BAD_REQUEST
    ):
        """
        Return standardized bad request response.
        Corresponds to: badRequestResponseSchema (400)
        """
        return Response(
            {"error": error_message},
            headers={"Content-Type": "application/json"},
            status=status_code,
        )

    def not_found_response(self, message):
        """
        Return standardized not found response.
        Corresponds to: notFoundResponseSchema (404)
        """
        return Response(
            {"error": message},
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_404_NOT_FOUND,
        )

    def not_acceptable_response(self, data, error_message):
        """
        Return standardized not acceptable response.
        Corresponds to: notAcceptableResponseSchema (406)
        """
        return Response(
            data={
                **data,
                "info": {"error": error_message},
            },
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_406_NOT_ACCEPTABLE,
        )

    def no_content_response(self, data=None, message=None):
        """
        Return standardized no content response.
        Corresponds to: noContentResponseSchema (204)
        """
        response_data = data or {}
        if message:
            response_data["message"] = message
        return Response(
            data=response_data,
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_204_NO_CONTENT,
        )

    def accepted_response(self, data):
        """
        Return standardized accepted response.
        Corresponds to: acceptedResponseSchema (202)
        """
        return Response(
            data,
            headers={"Content-Type": "application/json"},
            status=rest_framework.status.HTTP_202_ACCEPTED,
        )


# Specific response schemas for different endpoint types
vehicleSuccessResponseSchema = OpenApiResponse(
    response=VehicleSerializer,
    description="Vehicle operation completed successfully.",
)

vehicleListResponseSchema = OpenApiResponse(
    response=VehicleSerializer(many=True),
    description="List of vehicles retrieved successfully.",
)

vehicleTypeListResponseSchema = OpenApiResponse(
    response=inline_serializer(
        name="VehicleTypeListResponse",
        fields={
            "vessel_types": serializers.ListField(
                child=serializers.CharField(),
                help_text="List of available vessel types.",
            ),
        },
    ),
    description="List of available vessel types retrieved successfully.",
)

routeAcceptedResponseSchema = OpenApiResponse(
    response=inline_serializer(
        name="RouteAcceptedResponse",
        fields={
            "id": serializers.UUIDField(help_text="Job ID for route calculation"),
            "status-url": serializers.URLField(help_text="URL to check job status"),
            "polarrouteserver-version": serializers.CharField(
                help_text="Server version"
            ),
            "info": serializers.DictField(
                required=False, help_text="Additional information"
            ),
        },
    ),
    description="Route calculation job accepted.",
)

routeStatusResponseSchema = OpenApiResponse(
    response=inline_serializer(
        name="RouteStatusResponse",
        fields={
            "id": serializers.UUIDField(help_text="Job ID"),
            "status": serializers.CharField(help_text="Job status"),
            "polarrouteserver-version": serializers.CharField(
                help_text="Server version"
            ),
            "start_lat": serializers.FloatField(),
            "start_lon": serializers.FloatField(),
            "end_lat": serializers.FloatField(),
            "end_lon": serializers.FloatField(),
            "start_name": serializers.CharField(allow_null=True),
            "end_name": serializers.CharField(allow_null=True),
            "info": serializers.DictField(
                required=False, help_text="Additional info or errors"
            ),
        },
    ),
    description="Route status retrieved successfully.",
)

recentRoutesResponseSchema = OpenApiResponse(
    response=inline_serializer(
        name="RecentRoutesResponse",
        fields={
            "routes": serializers.ListField(
                child=serializers.DictField(),
                help_text="List of recent routes with status information",
            ),
        },
    ),
    description="List of recent routes retrieved successfully.",
)

meshDetailResponseSchema = OpenApiResponse(
    response=inline_serializer(
        name="MeshDetailResponse",
        fields={
            "polarrouteserver-version": serializers.CharField(
                help_text="Server version"
            ),
            "id": serializers.UUIDField(help_text="Mesh ID"),
            "json": serializers.JSONField(help_text="Mesh JSON data"),
            "geojson": serializers.JSONField(help_text="Mesh GeoJSON data"),
        },
    ),
    description="Mesh details retrieved successfully.",
)

routeEvaluationResponseSchema = OpenApiResponse(
    response=inline_serializer(
        name="RouteEvaluationResponse",
        fields={
            "polarrouteserver-version": serializers.CharField(
                help_text="Server version"
            ),
            "evaluation_results": serializers.DictField(
                help_text="Route evaluation results"
            ),
        },
    ),
    description="Route evaluated successfully.",
)

successResponseSchema = OpenApiResponse(
    response=inline_serializer(
        name="SuccessResponse",
        fields={
            "data": serializers.JSONField(help_text="Response data"),
        },
    ),
    description="Operation completed successfully.",
)

badRequestResponseSchema = OpenApiResponse(
    response=inline_serializer(
        name="BadRequestResponse",
        fields={
            "error": serializers.CharField(
                help_text="Error message describing what went wrong."
            ),
        },
    ),
    description="Bad request - invalid input data or malformed request.",
)

notFoundResponseSchema = OpenApiResponse(
    response=inline_serializer(
        name="NotFoundResponse",
        fields={
            "error": serializers.CharField(
                help_text="Error message indicating resource not found."
            ),
        },
    ),
    description="Requested resource not found.",
)

notAcceptableResponseSchema = OpenApiResponse(
    response=inline_serializer(
        name="NotAcceptableResponse",
        fields={
            "info": serializers.DictField(
                help_text="Details about the conflict, including error message."
            ),
        },
    ),
    description="Not acceptable - request conflicts with current resource state.",
)

noContentResponseSchema = OpenApiResponse(
    response=inline_serializer(
        name="NoContentResponse",
        fields={
            "message": serializers.CharField(
                required=False,
                help_text="Optional message describing the empty result.",
            ),
        },
    ),
    description="No content available.",
)

acceptedResponseSchema = OpenApiResponse(
    response=inline_serializer(
        name="AcceptedResponse",
        fields={
            "data": serializers.JSONField(
                help_text="Response data for accepted request"
            ),
        },
    ),
    description="Request accepted for processing.",
)

# No mesh OpenApiResponse object for Open API schema (matches no_mesh_response method)
noMeshResponseSchema = OpenApiResponse(
    response=inline_serializer(
        name="NoMeshResponse",
        fields={
            "info": serializers.DictField(
                help_text="Error message indicating no mesh found."
            ),
            "status": serializers.CharField(
                help_text="Status of the request (e.g., FAILURE)."
            ),
        },
    ),
    description="No matching mesh found.",
)
