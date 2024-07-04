import enum
import logging

from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class Status(enum.Enum):
    PENDING = enum.auto()
    RUNNING = enum.auto()
    FAILED = enum.auto()
    COMPLETED = enum.auto()


class PolarRouteModel(models.Model):
    "Abstract base class for common properties and methods of route and mesh models."

    id = models.BigAutoField(primary_key=True)
    requested = models.DateTimeField(null=True)
    calculated = models.DateTimeField(null=True)
    file = models.FilePathField(null=True, blank=True)
    status = models.TextField(null=True)

    class Meta:
        abstract = True

    def to_dict(self):
        "Return the object as a dict"
        pass


class Mesh(PolarRouteModel):
    # some mesh properties?
    pass


class Route(PolarRouteModel):
    mesh = models.ForeignKey(Mesh, on_delete=models.DO_NOTHING, null=True)
    waypoint_start_lat = models.FloatField()
    waypoint_start_lon = models.FloatField()
    waypoint_end_lat = models.FloatField()
    waypoint_end_lon = models.FloatField()


class Job(models.Model):
    "Route or mesh calculation jobs"

    id = models.UUIDField(
        primary_key=True
    )  # use uuids for primary keys to align with celery

    # job should correspond to mesh OR route, not both
    mesh = models.ForeignKey(Mesh, on_delete=models.DO_NOTHING, null=True)
    route = models.ForeignKey(Route, on_delete=models.DO_NOTHING, null=True)

    datetime = models.DateTimeField(default=timezone.now)
    status = models.TextField(null=True)
