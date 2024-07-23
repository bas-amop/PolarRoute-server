import logging

from celery.result import AsyncResult
from django.db import models
from django.utils import timezone

from polarrouteserver.celery import app

logger = logging.getLogger(__name__)


class PolarRouteModel(models.Model):
    "Abstract base class for common properties and methods of route and mesh models."

    id = models.BigAutoField(primary_key=True)
    requested = models.DateTimeField(default=timezone.now)
    calculated = models.DateTimeField(null=True)
    file = models.FilePathField(null=True, blank=True)
    status = models.TextField(null=True)

    class Meta:
        abstract = True

    def to_dict(self):
        "Return the object as a dict"
        raise NotImplementedError


class Mesh(PolarRouteModel):
    # some mesh properties?
    pass


class Route(PolarRouteModel):
    mesh = models.ForeignKey(Mesh, on_delete=models.DO_NOTHING, null=True)
    start_lat = models.FloatField()
    start_lon = models.FloatField()
    end_lat = models.FloatField()
    end_lon = models.FloatField()
    json = models.JSONField(null=True)


class Job(models.Model):
    "Route or mesh calculation jobs"

    id = models.UUIDField(
        primary_key=True
    )  # use uuids for primary keys to align with celery

    # job should correspond to mesh OR route, not both
    mesh = models.ForeignKey(Mesh, on_delete=models.DO_NOTHING, null=True)
    route = models.ForeignKey(Route, on_delete=models.DO_NOTHING, null=True)

    datetime = models.DateTimeField(default=timezone.now)

    @property
    def status(self):
        result = AsyncResult(self.id, app=app)
        return result.state
