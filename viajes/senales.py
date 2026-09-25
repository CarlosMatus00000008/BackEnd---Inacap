"""
Señales (acciones automáticas) de la app de viajes.

- crear_grupo_viajeros: crea el grupo «Viajeros» con los permisos de Django
  necesarios para usar el diario (ver, crear, editar y eliminar).
"""

from django.apps import apps as apps_globales
from django.db import DEFAULT_DB_ALIAS

GRUPO_VIAJEROS = "Viajeros"
MODELOS_CON_CRUD = ("viaje",)
ACCIONES = ("view", "add", "change", "delete")


def codigos_permisos_viajeros() -> list[str]:
    codigos = [f"{accion}_{modelo}" for modelo in MODELOS_CON_CRUD for accion in ACCIONES]
    return [*codigos, "view_pais"]


def crear_grupo_viajeros(sender, using=DEFAULT_DB_ALIAS, apps=apps_globales, **kwargs):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    grupo, _ = Group.objects.using(using).get_or_create(name=GRUPO_VIAJEROS)
    permisos = Permission.objects.using(using).filter(
        content_type__app_label="viajes", codename__in=codigos_permisos_viajeros()
    )
    grupo.permissions.add(*permisos)
