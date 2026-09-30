"""Pruebas del comando que crea el usuario demo «JuanPablo» (las descargas se simulan)."""

import shutil
import tempfile
from datetime import date
from io import BytesIO, StringIO
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from viajes.models import EstadoViaje, FotoViaje, Gasto, Viaje
from viajes.senales import GRUPO_VIAJEROS


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
        descarga = mock.patch("viajes.demo.descargar", return_value=jpg())
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
        self.assertTrue(cusco.notas.startswith("Fui con mi hermano."))
        self.assertNotIn("Wikimedia", cusco.notas)  # los créditos van en cada foto, no en las notas
        self.assertEqual(cusco.fotos.first().credito, "Diego Delso · CC BY-SA 4.0 · Wikimedia Commons")
        self.assertIn("Fotos subidas: 100 · con error: 0", salida)

    def test_completa_los_datos_de_registro(self):
        self.cargar()
        usuario = get_user_model().objects.get(username="JuanPablo")
        self.assertEqual(usuario.get_full_name(), "Juan Pablo Rojas Valenzuela")
        self.assertEqual(usuario.email, "juanpablo.rojas.viajes@gmail.com")
        self.assertEqual(usuario.date_joined.date(), date(2021, 4, 20))
        self.assertIsNotNone(usuario.last_login)
        self.assertEqual(usuario.perfil.telefono, "+56912345678")
        self.assertTrue(usuario.perfil.acepta_datos)
        self.assertEqual(usuario.perfil.fecha_consentimiento, usuario.date_joined)
        self.assertTrue(usuario.groups.filter(name=GRUPO_VIAJEROS).exists())

    def test_rellena_el_perfil_de_un_usuario_ya_creado(self):
        self.cargar()
        get_user_model().objects.filter(username="JuanPablo").update(email="", last_name="")
        self.cargar()
        usuario = get_user_model().objects.get(username="JuanPablo")
        self.assertEqual((usuario.email, usuario.last_name), ("juanpablo.rojas.viajes@gmail.com", "Rojas Valenzuela"))
        self.assertEqual(FotoViaje.objects.count(), 100)  # no duplica fotos

    def test_repetirlo_solo_completa_las_fotos_que_faltan(self):
        self.cargar()
        sobrantes = FotoViaje.objects.filter(viaje__pais__codigo_iso="IS").values_list("pk", flat=True)[:3]
        FotoViaje.objects.filter(pk__in=list(sobrantes)).delete()
        self.descargar.reset_mock()
        self.cargar()
        self.assertEqual(self.descargar.call_count, 3)
        self.assertEqual(FotoViaje.objects.count(), 100)

    def test_repetirlo_pone_al_dia_notas_y_creditos(self):
        self.cargar()
        cusco = Viaje.objects.get(usuario__username="JuanPablo", pais__codigo_iso="PE")
        Viaje.objects.filter(pk=cusco.pk).update(notas="Notas antiguas con créditos amontonados")
        cusco.fotos.update(credito="")
        self.cargar()
        cusco.refresh_from_db()
        self.assertTrue(cusco.notas.startswith("Fui con mi hermano."))
        self.assertFalse(cusco.fotos.filter(credito="").exists())

    def test_eliminar_borra_usuario_y_archivos(self):
        self.cargar()
        with self.captureOnCommitCallbacks(execute=True):  # los archivos se borran al confirmar
            self.cargar("--eliminar")
        self.assertFalse(get_user_model().objects.filter(username="JuanPablo").exists())
        self.assertFalse(FotoViaje.objects.exists())
        self.assertEqual(list(Path(self.carpeta).rglob("*.jpg")), [])
