from django.apps import AppConfig


class BackendConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "polarrouteserver.route_api"

    def ready(self):
        import polarrouteserver.route_api.signals
