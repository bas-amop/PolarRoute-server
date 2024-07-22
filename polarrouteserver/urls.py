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

from route_api import views

# API_PREFIX_V0 = "api/v0/" # common url prefix for all version 0 api endpoints (for futureproofing)

urlpatterns = [
    path("admin/", admin.site.urls),
    # TODO these urls are duplicated here for future back-compatibility, there's probably a better way of doing this
    path("api/route", views.RouteView.as_view(), name="route"),
    path("api/status/<uuid:id>", views.StatusView.as_view(), name="status"),
    # path(API_PREFIX_V0 + "route/", views.RouteView.as_view(), name="route"),
    # path(API_PREFIX_V0 + "status/<str:id>", views.StatusView.as_view(), name="status"),
]
