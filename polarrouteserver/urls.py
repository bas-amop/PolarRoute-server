"""
URL configuration for polarrouteserver project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from polarrouteserver.route_api import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/route",
        views.RouteRequestView.as_view(),
        name="route_list_create",
    ),
    path(
        "api/route/<uuid:id>",
        views.RouteDetailView.as_view(),
        name="route_detail",
    ),
    path(
        "api/recent_routes",
        views.RecentRoutesView.as_view(),
        name="recent_routes_list",
    ),
    path(
        "api/vehicle",
        views.VehicleRequestView.as_view(),  # POST and GET (list all)
        name="vehicle_list_create",
    ),
    path(
        "api/vehicle/<str:vessel_type>/",
        views.VehicleDetailView.as_view(),  # GET/DELETE by vessel_type
        name="vehicle_detail",
    ),
    path(
        "api/vehicle/available",
        views.VehicleTypeListView.as_view(),
        name="vehicle_type_list",
    ),
    path("api/mesh/<int:id>", views.MeshView.as_view(), name="mesh_detail"),
    path(
        "api/evaluate_route", views.EvaluateRouteView.as_view(), name="evaluate_route"
    ),
]

# noqa
try:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += debug_toolbar_urls()
except:  # noqa
    pass
