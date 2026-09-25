"""
Diagnóstico de la conexión a la base de datos.

Lo usan el comando «python manage.py verificar_bd», la ruta /salud/ y el panel
de administración para confirmar que la conexión está activa.
"""

import time
from dataclasses import dataclass

from django.db import DatabaseError, connection
from django.db.migrations.executor import MigrationExecutor


@dataclass
class EstadoBaseDatos:
    conectada: bool = False
    motor: str = ""
    version: str = ""
    nombre: str = ""
    latencia_ms: float | None = None
    migraciones_pendientes: int | None = None
    error: str = ""


def diagnosticar(incluir_migraciones: bool = True) -> EstadoBaseDatos:
    """Se conecta, mide la latencia y revisa las migraciones (sin exponer datos sensibles)."""
    estado = EstadoBaseDatos(motor=connection.display_name, nombre=str(connection.settings_dict.get("NAME") or ""))

    try:
        inicio = time.perf_counter()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        estado.latencia_ms = round((time.perf_counter() - inicio) * 1000, 1)
        estado.version = ".".join(str(parte) for parte in connection.get_database_version())
        estado.conectada = True
    except DatabaseError as error:
        mensaje = str(error).strip()
        estado.error = mensaje.splitlines()[0] if mensaje else error.__class__.__name__
        return estado

    if incluir_migraciones:
        try:
            ejecutor = MigrationExecutor(connection)
            plan = ejecutor.migration_plan(ejecutor.loader.graph.leaf_nodes())
            estado.migraciones_pendientes = len(plan)
        except DatabaseError:
            estado.migraciones_pendientes = None

    return estado
