"""Pruebas de las piezas compartidas: base de datos, errores, filtros y sanitización."""

from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from core.templatetags.diario import dias, hace, miles
from core.texto import limpiar_linea, limpiar_parrafos


class BaseDeDatosTests(TestCase):
    def test_salud_responde_json(self):
        respuesta = self.client.get(reverse("core:salud"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["estado"], "ok")
        self.assertTrue(respuesta.json()["base_de_datos"]["conectada"])

    def test_comando_verificar_bd(self):
        salida = StringIO()
        call_command("verificar_bd", stdout=salida)
        self.assertIn("Migraciones al día", salida.getvalue())

    def test_modelos_y_migraciones_sincronizados(self):
        """Si alguien cambia un modelo y olvida crear la migración, esta prueba falla."""
        call_command("makemigrations", "--check", "--dry-run", stdout=StringIO())


class PaginasDeErrorTests(TestCase):
    @override_settings(DEBUG=False)
    def test_404_personalizado(self):
        respuesta = self.client.get("/esta-pagina-no-existe/")
        self.assertEqual(respuesta.status_code, 404)
        self.assertContains(respuesta, "No encontramos esta página", status_code=404)

    def test_inicio_publico(self):
        self.assertContains(self.client.get(reverse("core:inicio")), "Crear mi diario gratis")


class FiltrosTests(TestCase):
    def test_miles(self):
        self.assertEqual(miles(1500000), "1.500.000")
        self.assertEqual(miles(999), "999")
        self.assertEqual(dias(1250), "1.250 días")

    def test_dias(self):
        self.assertEqual(dias(1), "1 día")
        self.assertEqual(dias(4), "4 días")

    def test_hace(self):
        hoy = timezone.localdate()
        self.assertEqual(hace(hoy), "hoy")
        self.assertEqual(hace(hoy - timedelta(days=3)), "hace 3 días")
        self.assertEqual(hace(hoy - timedelta(days=65)), "hace 2 meses")
        self.assertEqual(hace(hoy - timedelta(days=800)), "hace 2 años")


class SanitizacionTests(TestCase):
    def test_limpiar_linea(self):
        self.assertEqual(limpiar_linea("  <b>Hola</b>\t​mundo  "), "Hola mundo")

    def test_limpiar_parrafos_conserva_saltos(self):
        self.assertEqual(limpiar_parrafos("Línea 1\r\n\r\n\r\n<i>Línea 2</i>  "), "Línea 1\n\nLínea 2")
