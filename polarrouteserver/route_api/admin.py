from django.contrib import admin
from django.db.models import Prefetch
from .models import Route, Mesh, Job

LIST_PER_PAGE = 20


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
    list_select_related = ("mesh",)

    def get_queryset(self, request):
        # Just select mesh, ie the ForeignKey
        queryset = super().get_queryset(request).select_related("mesh")

        # Use prefetch to get the jobs with a single query
        job_queryset = Job.objects.order_by("-datetime")
        queryset = queryset.prefetch_related(
            Prefetch("job_set", queryset=job_queryset, to_attr="prefetched_jobs")
        )

        return queryset

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
        if not hasattr(obj, "prefetched_jobs") or not obj.prefetched_jobs:
            return "-"
        return f"{obj.prefetched_jobs[0].id}"

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


admin.site.register(Route, RouteAdmin)
admin.site.register(Mesh, MeshAdmin)
admin.site.register(Job, JobAdmin)
