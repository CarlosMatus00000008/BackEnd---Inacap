"""Pruebas del comando que crea los usuarios demo Valentina y Matias (las descargas se simulan)."""

import shutil
import tempfile
from io import StringIO
from unittest import mock

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings

from viajes.models import EstadoViaje, FotoViaje, Viaje

from .test_cargar_juanpablo import jpg


class CargarViajerosDemoTests(TestCase):
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
        descarga.start()
        self.addCleanup(descarga.stop)

    def cargar(self, *argumentos):
        call_command("cargar_viajeros_demo", *argumentos, stdout=StringIO(), stderr=StringIO())

    def test_crea_a_valentina_y_matias_con_todo_relleno(self):
        self.cargar()
        valentina = authenticate(username="Valentina", password="Valentina123")
        matias = authenticate(username="Matias", password="Matias123")
        self.assertEqual((valentina.viajes.count(), matias.viajes.count()), (5, 8))
        self.assertEqual(valentina.email, "valentina.soto.viajes@gmail.com")
        self.assertEqual(matias.get_full_name(), "Matías Fuentes Araya")
        self.assertTrue(matias.perfil.acepta_datos)
        # 10 fotos por viaje hecho o en curso: 4 de Valentina + 7 de Matías.
        self.assertEqual(FotoViaje.objects.count(), 110)
        for viaje in Viaje.objects.exclude(estado=EstadoViaje.PLANIFICADO):
            self.assertTrue(viaje.actividades.exists(), viaje)
            self.assertTrue(viaje.gastos.exists(), viaje)

    def test_viaje_en_curso_con_lo_pasado_marcado_como_hecho(self):
        self.cargar()
        sidney = Viaje.objects.get(usuario__username="Matias", estado=EstadoViaje.EN_PROGRESO)
        self.assertTrue(sidney.actividades.filter(realizada=True).exists())
        self.assertTrue(sidney.actividades.filter(realizada=False).exists())

    def test_viaje_en_chile_con_gastos_solo_en_pesos(self):
        self.cargar()
        paine = Viaje.objects.get(usuario__username="Matias", pais__codigo_iso="CL")
        self.assertFalse(paine.gastos.exclude(moneda="").exists())
        self.assertEqual(paine.gastos.get(descripcion="Entrada al parque").monto, 49_000)

    def test_se_comparten_un_viaje_entre_ellos(self):
        self.cargar()
        valentina, matias = (get_user_model().objects.get(username=n) for n in ("Valentina", "Matias"))
        self.assertEqual([v.destino for v in Viaje.objects.compartidos_con(matias)], ["Atenas y Santorini"])
        self.assertEqual([v.destino for v in Viaje.objects.compartidos_con(valentina)], ["Londres y Edimburgo"])

    def test_repetirlo_no_duplica_y_eliminar_borra_ambos(self):
        self.cargar()
        self.cargar()
        self.assertEqual((Viaje.objects.count(), FotoViaje.objects.count()), (13, 110))
        self.cargar("--eliminar")
        self.assertFalse(get_user_model().objects.filter(username__in=["Valentina", "Matias"]).exists())
