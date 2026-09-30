"""Pruebas del comando que crea el usuario demo «JuanPablo» (las descargas se simulan)."""

import shutil
import tempfile
from io import BytesIO, StringIO
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from viajes.management.commands.cargar_juanpablo import Command
from viajes.models import EstadoViaje, FotoViaje, Gasto


def jpg():
    salida = BytesIO()
    Image.new("RGB", (192, 108), "#2563eb").save(salida, "JPEG")
    return salida.getvalue()


class CargarJuanPabloTests(TestCase):
    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        ajustes = override_settings(
            MEDIA_ROOT=self.carpeta,
            FOTOS_HABILITADAS=True,
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            },
        )
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        self.addCleanup(shutil.rmtree, self.carpeta, ignore_errors=True)
        descarga = mock.patch.object(Command, "_descargar", return_value=jpg())
        self.descargar = descarga.start()
        self.addCleanup(descarga.stop)

    def cargar(self, *argumentos):
        salida = StringIO()
        call_command("cargar_juanpablo", *argumentos, stdout=salida, stderr=StringIO())
        return salida.getvalue()

    def test_crea_usuario_viajes_gastos_y_10_fotos_por_pais(self):
        salida = self.cargar("--contrasena", "Clave.Segura.2026")
        usuario = get_user_model().objects.get(username="JuanPablo")
        self.assertTrue(usuario.check_password("Clave.Segura.2026"))
        self.assertEqual(usuario.viajes.filter(estado=EstadoViaje.COMPLETADO).count(), 10)
        self.assertEqual(usuario.viajes.filter(estado=EstadoViaje.PLANIFICADO).count(), 2)
        self.assertEqual(FotoViaje.objects.filter(viaje__usuario=usuario).count(), 100)
        self.assertTrue(Gasto.objects.filter(viaje__usuario=usuario, moneda="JPY").exists())
        cusco = usuario.viajes.get(pais__codigo_iso="PE")
        self.assertIn("📷 Fotos de Wikimedia Commons", cusco.notas)  # crédito de las licencias
        self.assertIn("Fotos subidas: 100 · con error: 0", salida)

    def test_repetirlo_solo_completa_las_fotos_que_faltan(self):
        self.cargar()
        sobrantes = FotoViaje.objects.filter(viaje__pais__codigo_iso="IS").values_list("pk", flat=True)[:3]
        FotoViaje.objects.filter(pk__in=list(sobrantes)).delete()
        self.descargar.reset_mock()
        self.cargar()
        self.assertEqual(self.descargar.call_count, 3)
        self.assertEqual(FotoViaje.objects.count(), 100)

    def test_eliminar_borra_usuario_y_archivos(self):
        self.cargar()
        with self.captureOnCommitCallbacks(execute=True):  # los archivos se borran al confirmar
            self.cargar("--eliminar")
        self.assertFalse(get_user_model().objects.filter(username="JuanPablo").exists())
        self.assertFalse(FotoViaje.objects.exists())
        self.assertEqual(list(Path(self.carpeta).rglob("*.jpg")), [])
