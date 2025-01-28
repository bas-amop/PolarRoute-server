import logging

from celery.result import AsyncResult
from django.contrib.gis.db import models
from django.contrib.gis.geos import MultiPolygon, GEOSGeometry
from django.utils import timezone

from meshiphi.mesh_generation.environment_mesh import EnvironmentMesh
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
    _geom = models.MultiPolygonField(srid=4326, null=True)

    @property
    def size(self) -> float:
        """Computes a metric for the size of a mesh."""

        return abs(self.lat_max - self.lat_min) * abs(self.lon_max - self.lon_min)

    @property
    def geojson(self) -> dict:
        """Returns Mesh as GeoJSON"""

        return EnvironmentMesh.load_from_json(self.json).to_geojson()
    
    @property
    def geom(self):
        """Getter for geom property."""
        if not self._geom:
            self.set_geom_from_geojson()
        return self._geom
            

    def set_geom_from_geojson(self) -> None:
        data = self.geojson
        polygons = []
        for feature in data['features']:

            polygon = GEOSGeometry(str(feature['geometry']))
            polygons.append(polygon)

        self._geom = MultiPolygon(polygons, srid=4326)
        self.save()


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
