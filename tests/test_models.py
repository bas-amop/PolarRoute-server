from django.contrib.gis.geos import MultiPolygon
from django.test import TestCase

from polarrouteserver.route_api.models import Mesh
from .utils import add_test_mesh_to_db

class TestMesh(TestCase):

    def setUp(self):
        self.mesh = add_test_mesh_to_db()
        
    def test_get_geom(self):
        self.assertIsInstance(self.mesh.geom, MultiPolygon)