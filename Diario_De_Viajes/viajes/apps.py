from django.apps import AppConfig


class ViajesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "viajes"

    def ready(self):
        import viajes.signals  # noqa: F401  (registra las señales al arrancar)
