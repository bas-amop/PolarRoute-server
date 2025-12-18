import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from polarrouteserver.route_api.models import Mesh, MeshPolygon

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Mesh)
def create_mesh_polygons_on_mesh_save(sender, instance, created, raw, using, update_fields, **kwargs):

    print(
        f"sender: {sender} \n"
        f"instance: {instance} \n"
        f"created: {created} \n"
        f"raw: {raw} \n"
        f"using: {using} \n"
        f"update_fields: {update_fields}"
    )

    
    if not instance.json:
        logger.warning(f"Mesh id: {instance.id} saved with no json. Won't create mesh polygons.")
        return
    
    # if newly created, or json has been updated
    if created is True or (update_fields is not None and "json" in update_fields):
        MeshPolygon.create_from_mesh(instance.id)