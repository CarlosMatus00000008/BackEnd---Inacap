"""
Comprueba la conexión con la base de datos y muestra un resumen.

Uso:
    python manage.py verificar_bd
"""

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from core.basedatos import diagnosticar

MODELOS_A_CONTAR = [
    ("auth", "User", "Usuarios"),
    ("viajes", "Pais", "Países"),
    ("viajes", "Viaje", "Viajes"),
]


class Command(BaseCommand):
    help = "Verifica la conexión a la base de datos (motor, versión, latencia y migraciones)."

    def handle(self, *args, **opciones):
        self.stdout.write(self.style.MIGRATE_HEADING("Verificando la base de datos..."))
        estado = diagnosticar()

        if not estado.conectada:
            raise CommandError(f"No se pudo conectar a {estado.motor}.\nDetalle: {estado.error}")

        for etiqueta, valor in (
            ("Motor", f"{estado.motor} {estado.version}"),
            ("Base de datos", estado.nombre),
            ("Latencia", f"{estado.latencia_ms} ms"),
        ):
            self.stdout.write(f"  {etiqueta:<16} {valor}")

        if estado.migraciones_pendientes:
            self.stdout.write(
                self.style.WARNING(
                    f"  Hay {estado.migraciones_pendientes} migraciones pendientes → "
                    "ejecuta «python manage.py migrate»."
                )
            )
        elif estado.migraciones_pendientes == 0:
            self.stdout.write(self.style.SUCCESS("  Migraciones al día."))
            self._contar_registros()

        self.stdout.write(self.style.SUCCESS("Conexión con la base de datos activa y verificada."))

    def _contar_registros(self):
        self.stdout.write("  Registros:")
        for app_label, nombre_modelo, etiqueta in MODELOS_A_CONTAR:
            try:
                total = apps.get_model(app_label, nombre_modelo).objects.count()
            except DatabaseError:
                total = "sin tabla"
            self.stdout.write(f"    - {etiqueta:<14} {total}")
