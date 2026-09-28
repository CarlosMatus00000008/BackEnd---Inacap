"""
Señales (acciones automáticas) de la app de viajes.

- crear_grupo_viajeros: crea el grupo «Viajeros» con los permisos de Django
  necesarios para usar el diario (ver, crear, editar y eliminar).
- borrar_archivo_foto: al eliminar una foto (o el viaje completo) también
  borra el archivo del almacenamiento (Supabase Storage), para no dejar basura.
"""

import logging

from django.apps import apps as apps_globales
from django.db import DEFAULT_DB_ALIAS, transaction

logger = logging.getLogger("viajes")

GRUPO_VIAJEROS = "Viajeros"
MODELOS_CON_CRUD = ("viaje", "actividad", "gasto", "fotoviaje")
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


def borrar_archivo_foto(sender, instance, **kwargs):
    archivo = instance.imagen
    if not archivo:
        return
    nombre, almacenamiento = archivo.name, archivo.storage

    def borrar():
        try:
            almacenamiento.delete(nombre)
        except Exception:
            # Si el almacenamiento falla, la foto ya no aparece en el sitio: solo queda registrado.
            logger.exception("No se pudo borrar el archivo %s", nombre)

    # Se borra solo si la eliminación en la base de datos se confirma.
    transaction.on_commit(borrar)
