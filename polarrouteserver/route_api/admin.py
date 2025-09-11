from django.contrib import admin

from .models import Vehicle, Route, Job, VehicleMesh, EnvironmentMesh

# Shared list_display for all mesh-based admin classes
MESH_LIST_DISPLAY = [
    "id",
    "valid_date_start",
    "valid_date_end",
    "created",
    "lat_min",
    "lat_max",
    "lon_min",
    "lon_max",
    "name",
    "size",
]


# Shared base admin for mesh models
class BaseMeshAdmin(admin.ModelAdmin):
    ordering = ("-created",)
    readonly_fields = ("md5", "size", "created")
    exclude = ("json",)  # Hide the raw JSON field
    list_per_page = 20

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.defer("json")

        if hasattr(self, "list_select_related") and self.list_select_related:
            queryset = queryset.select_related(*self.list_select_related)

        return queryset


class VehicleMeshAdmin(BaseMeshAdmin):
    list_display = ["id", "vehicle"] + MESH_LIST_DISPLAY[1:]
    list_select_related = ("vehicle",)
    list_filter = ("vehicle", "created")
    search_fields = ("name", "vehicle__vessel_type")


class EnvironmentMeshAdmin(BaseMeshAdmin):
    list_display = MESH_LIST_DISPLAY
    list_filter = ("created",)
    search_fields = ("name",)


LIST_PER_PAGE = 20


class VehicleAdmin(admin.ModelAdmin):
    list_display = ["vessel_type"]


class RouteAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "display_start",
        "display_end",
        "vehicle_type",
        "requested",
        "calculated",
        "job_id",
        "mesh_id",
        "info",
        "polar_route_version",
    ]
    ordering = ("-requested",)

    def get_queryset(self, request):
        # Load only the fields necessary for the changelist view
        queryset = super().get_queryset(request)
        return queryset.only(
            "id",
            "start_lat",
            "start_lon",
            "end_lat",
            "end_lat",
            "requested",
            "calculated",
            "job",
            "mesh_id",
            "vehicle_id",
            "info",
            "polar_route_version",
        )

    list_select_related = ("mesh", "vehicle")

    def display_start(self, obj):
        if obj.start_name:
            return f"{obj.start_name} ({obj.start_lat},{obj.start_lon})"
        else:
            return f"({obj.start_lat},{obj.start_lon})"

    def display_end(self, obj):
        if obj.end_name:
            return f"{obj.end_name} ({obj.end_lat},{obj.end_lon})"
        else:
            return f"({obj.end_lat},{obj.end_lon})"

    def job_id(self, obj):
        if obj.job_set.count() == 0:
            return "-"
        else:
            job = obj.job_set.latest("datetime")
            return f"{job.id}"

    def mesh_id(self, obj):
        if obj.mesh:
            return f"{obj.mesh.id}"

    def vehicle_type(self, obj):
        if obj.vehicle:
            return obj.vehicle.vessel_type
        return "-"

    display_start.short_description = "Start (lat,lon)"
    display_end.short_description = "End (lat,lon)"
    job_id.short_description = "Job ID (latest)"
    mesh_id.short_description = "Mesh ID"
    vehicle_type.short_description = "Vehicle Type"


class JobAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "datetime",
        "route",
        "status",
    ]
    ordering = ("-datetime",)


admin.site.register(Vehicle, VehicleAdmin)
admin.site.register(Route, RouteAdmin)
admin.site.register(Job, JobAdmin)
admin.site.register(VehicleMesh, VehicleMeshAdmin)
admin.site.register(EnvironmentMesh, EnvironmentMeshAdmin)
