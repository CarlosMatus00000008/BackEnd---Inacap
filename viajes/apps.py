from django.apps import AppConfig
from django.db.models.signals import post_migrate


class ViajesConfig(AppConfig):
    name = "viajes"
    verbose_name = "Diario de viajes"

    def ready(self):
        from . import senales

        # Después de cada «migrate» se asegura que exista el grupo «Viajeros»
        # con sus permisos (se ejecuta después de que Django crea los permisos).
        post_migrate.connect(senales.crear_grupo_viajeros, sender=self)
