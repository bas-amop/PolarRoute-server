import enum
from django.db import models

class Status(enum.Enum):
    PENDING = enum.auto()
    RUNNING = enum.auto()
    FAILED = enum.auto()
    COMPLETED = enum.auto()

class PolarRouteModel(models.Model):
    "Abstract base class for common properties and methods of route and mesh models."
    id = models.IntegerField(primary_key=True)
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
    waypoint_start = models.JSONField(blank=True)
    waypoint_end = models.JSONField(blank=True)
