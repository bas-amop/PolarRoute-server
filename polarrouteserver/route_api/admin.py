from django.contrib import admin

from .models import Vehicle, Route, Mesh, Job

LIST_PER_PAGE = 20


class VehicleAdmin(admin.ModelAdmin):
    list_display = ["vessel_type"]


class RouteAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "display_start",
        "display_end",
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
            "info",
            "polar_route_version",
        )

    list_select_related = ("mesh",)

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

    display_start.short_description = "Start (lat,lon)"
    display_end.short_description = "End (lat,lon)"
    job_id.short_description = "Job ID (latest)"
    mesh_id.short_description = "Mesh ID"


class JobAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "datetime",
        "route",
        "status",
    ]
    ordering = ("-datetime",)


class MeshAdmin(admin.ModelAdmin):
    list_display = [
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
    ordering = ("-created",)


admin.site.register(Vehicle, VehicleAdmin)
admin.site.register(Route, RouteAdmin)
admin.site.register(Mesh, MeshAdmin)
admin.site.register(Job, JobAdmin)
