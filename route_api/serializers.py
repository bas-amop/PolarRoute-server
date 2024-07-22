from rest_framework import serializers


class PolarRouteSerializer(serializers.Serializer):
    id = serializers.IntegerField()

    class Meta:
        abstract = True


class RouteSerializer(PolarRouteSerializer):
    start_lat = serializers.FloatField()
    start_lon = serializers.FloatField()
    end_lat = serializers.FloatField()
    end_lon = serializers.FloatField()
