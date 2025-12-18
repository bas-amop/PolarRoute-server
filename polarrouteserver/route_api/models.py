import logging

from celery.result import AsyncResult
from django.contrib.gis.db import models
from django.contrib.gis.geos import GEOSGeometry
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

class MeshPolygon(models.Model):
    default_srid=3857
    mesh = models.ForeignKey(Mesh, on_delete=models.CASCADE)
    properties = models.JSONField()
    geometry = models.GeometryField(srid=default_srid)
    # use 3857: web mercator as the default projection
    # we will store based on the most appropriate projection for a given mesh,
    # eg 3031: antarctic stereographic for south polar
    # or 3431 for north polar

    @classmethod
    def create_from_mesh(cls, mesh_id:int):
        # NOTE: This method is currently only called from the corresponding signal from a mesh save, see signals.py module.

        source_srid = 4326

        # get mesh object
        try:
            mesh = Mesh.objects.get(id=mesh_id)
        except Mesh.DoesNotExist:
            raise Exception
        
        # delete previous polygons for this mesh
        try:
            cls.objects.get(mesh=mesh).delete()
        except MeshPolygon.DoesNotExist:
            pass

        # create new mesh polygons
        new_polygons = []
        for feature in mesh.json['cellboxes']:
            geometry = feature.pop('geometry')
            properties = feature

            new_polygons.append(cls(
                mesh=mesh,
                properties=properties,
                geometry = GEOSGeometry(geometry, source_srid).transform(cls.default_srid, clone=True),
            ))

        cls.objects.bulk_create(new_polygons)
    
    class Meta:
        indexes = [
            models.Index(fields=['mesh']),
        ]

class Vehicle(models.Model):
    # Required properties
    vessel_type = models.CharField(
        max_length=150, default=None, unique=True, primary_key=True
    )
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
    route = models.ForeignKey(Route, on_delete=models.CASCADE)

    @property
    def status(self):
        result = AsyncResult(self.id, app=app)
        return result.state


class Location(models.Model):
    "Preset locations"

    lat = models.FloatField()
    lon = models.FloatField()
    name = models.CharField(max_length=100)

    @property
    def latitude(self):
        return self.lat

    @property
    def longitude(self):
        return self.lon
