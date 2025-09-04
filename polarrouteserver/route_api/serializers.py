from rest_framework import serializers

from .models import Mesh, Vehicle, Route, Location


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            "vessel_type",
            "max_speed",
            "unit",
            "max_ice_conc",
            "min_depth",
            "max_wave",
            "excluded_zones",
            "neighbour_splitting",
            "beam",
            "hull_type",
            "force_limit",
        ]


class VesselTypeSerializer(serializers.Serializer):
    class Meta:
        vessel_type = serializers.CharField()


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
            "mesh",
        ]

    def to_representation(self, instance):
        """Returns unsmoothed routes if available when smoothed routes have failed."""
        data = super().to_representation(instance)

        smoothed = {}
        unsmoothed = {}
        data["json"] = []
        for key in ("traveltime", "fuel"):
            smoothed[key] = (
                [
                    x
                    for x in data["json"]
                    if x[0]["features"][0]["properties"]["objective_function"] == key
                ]
                if data["json"] is not None
                else []
            )
            unsmoothed[key] = (
                [
                    x
                    for x in data["json_unsmoothed"]
                    if x[0]["features"][0]["properties"]["objective_function"] == key
                ]
                if data["json_unsmoothed"] is not None
                else []
            )

            # if there is no smoothed route available, use unsmoothed in its place
            if len(smoothed[key]) == 0 and len(unsmoothed[key]) == 1:
                data["json"].extend(unsmoothed[key])
                data["info"] = {
                    "error": f"Smoothing failed for {key}-optimisation, returning unsmoothed route."
                }
            elif len(smoothed[key]) == 0 and len(unsmoothed[key]) == 0:
                data["info"] = {"error": f"No routes available for {key}-optimisation."}
            else:
                data["json"].extend(unsmoothed[key])

        return data


class ModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mesh
        fields = [
            "id",
        ]

    def to_representation(self, instance):
        return super().to_representation(instance)


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = [
            "id",
            "lat",
            "lon",
            "name",
        ]
