import logging

from celery.result import AsyncResult
from django.db import models
from django.utils import timezone

from polarrouteserver.celery import app

logger = logging.getLogger(__name__)


class Mesh(models.Model):
    id = models.BigAutoField(primary_key=True)
    meshiphi_version = models.CharField(max_length=60, null=True)
    md5 = models.CharField(max_length=64)
    valid_date_start = models.DateField()
    valid_date_end = models.DateField()
    created = models.DateTimeField()
    lat_min = models.FloatField()
    lat_max = models.FloatField()
    lon_min = models.FloatField()
    lon_max = models.FloatField()
    json = models.JSONField(null=True)
    name = models.CharField(max_length=150, null=True)

    @property
    def size(self) -> float:
        """Computes a metric for the size of a mesh."""

        return abs(self.lat_max - self.lat_min) * abs(self.lon_max - self.lon_min)

    class Meta:
        verbose_name_plural = "Meshes"


class Route(models.Model):
    requested = models.DateTimeField(default=timezone.now)
    calculated = models.DateTimeField(null=True)
    info = models.JSONField(null=True)
    mesh = models.ForeignKey(Mesh, on_delete=models.SET_NULL, null=True)
    start_lat = models.FloatField()
    start_lon = models.FloatField()
    end_lat = models.FloatField()
    end_lon = models.FloatField()
    start_name = models.CharField(max_length=100, null=True, blank=True, default=None)
    end_name = models.CharField(max_length=100, null=True, blank=True, default=None)
    json = models.JSONField(null=True)
    json_unsmoothed = models.JSONField(null=True)
    polar_route_version = models.CharField(max_length=60, null=True)


class Vehicles(models.Model):
    # Required properties
    vessel_type = models.CharField(max_length=150, null=True, default=None, unique=True)
    max_speed = models.FloatField()
    unit = models.CharField(max_length=150)
    # Other properties defined in the schema
    max_ice_conc = models.FloatField(null=True)
    min_depth = models.FloatField(null=True)
    max_wave = models.FloatField(null=True)
    excluded_zones = models.JSONField(null=True)
    neighbour_splitting = models.BooleanField(null=True)
    # Additional properties - SDA
    beam = models.FloatField(null=True)
    hull_type = models.CharField(null=True, max_length=150)
    force_limit = models.FloatField(null=True)
    # Django-related fields
    created = models.DateTimeField(null=True)
    # Placeholder `created_by` may have future db relationship with users
    # e.g. models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_by = models.CharField(max_length=150, null=True)


class Job(models.Model):
    "Route or mesh calculation jobs"

    id = models.UUIDField(
        primary_key=True
    )  # use uuids for primary keys to align with celery

    datetime = models.DateTimeField(default=timezone.now)
    route = models.ForeignKey(Route, on_delete=models.SET_NULL, null=True)

    @property
    def status(self):
        result = AsyncResult(self.id, app=app)
        return result.state
