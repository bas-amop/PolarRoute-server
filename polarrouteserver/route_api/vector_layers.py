from vectortiles import VectorLayer

from .models import Mesh


class MeshVectorLayer(VectorLayer):
    model = Mesh
    id = "meshes"  # layer id in you vector layer. each class attribute can be defined by get_{attribute} method
    geom_field = "geom"
    tile_fields = ("valid_date_start", "valid_date_end")  # fields to include in tile
    min_zoom = 10  # minimum zoom level to include layer. Take care of this, as it could be a performance issue. Try to not embed data that will no be shown in your style definition.
    # all attributes available in vector layer definition can be defined
