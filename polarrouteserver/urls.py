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

import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from polarrouteserver.route_api import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/route", views.RouteView.as_view(), name="route"
    ),  # url for requesting(post)/deleting routes
    path(
        "api/route/<uuid:id>", views.RouteView.as_view(), name="route"
    ),  # url for retrieving routes (get)
    path("api/recent_routes", views.RecentRoutesView.as_view(), name="recent_routes"),
    path("api/mesh/<int:id>", views.MeshView.as_view(), name="mesh"),
    path(
        "api/evaluate_route", views.EvaluateRouteView.as_view(), name="evaluate_route"
    ),
]

if os.getenv("POLARROUTE_FRONTEND", True):
    import polarrouteserver.frontend  # noqa: F401

    urlpatterns.extend(
        [
            path("django_plotly_dash/", include("django_plotly_dash.urls")),
            path("", TemplateView.as_view(template_name="index.html"), name="frontend"),
        ]
    )

    # for serving static files in development
    if settings.DEBUG:
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
