from django.contrib import admin

from .models import Route, Mesh, Job


class RouteAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "display_start",
        "display_end",
        "start_name",
        "end_name",
        "requested",
        "calculated",
    ]

    def display_start(self, obj):
        return f"({obj.start_lat},{obj.start_lon})"

    def display_end(self, obj):
        return f"({obj.end_lat},{obj.end_lon})"

    display_start.short_description = "Start (lat,lon)"
    display_end.short_description = "End (lat,lon)"


admin.site.register(Route, RouteAdmin)
admin.site.register(Mesh)
admin.site.register(Job)
