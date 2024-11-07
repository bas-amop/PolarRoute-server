from rest_framework import serializers

from route_api.models import Route


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = [
            "start_lat",
            "start_lon",
            "end_lat",
            "end_lon",
            "start_name",
            "end_name",
            "json",
            "json_unsmoothed",
            "polar_route_version",
            "info",
        ]
