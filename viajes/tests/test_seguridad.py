"""Pruebas de seguridad: CSRF, cabeceras HTTP, cierre de sesión seguro y escape de HTML."""

from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse

from viajes.models import EstadoViaje, Viaje

from .utilidades import CONTRASENA, crear_usuario, crear_viaje, hoy


class CsrfTests(TestCase):
    def setUp(self):
        self.ana = crear_usuario("ana")
        # Este cliente SÍ exige el token CSRF (el cliente normal de pruebas lo omite).
        self.cliente = Client(enforce_csrf_checks=True)
        self.cliente.force_login(self.ana)

    def test_post_sin_token_es_rechazado_con_pagina_clara(self):
        viaje = crear_viaje(self.ana)
        respuesta = self.cliente.post(reverse("viajes:eliminar", args=[viaje.pk]))
        self.assertEqual(respuesta.status_code, 403)
        self.assertContains(respuesta, "protección CSRF", status_code=403)
        self.assertTrue(Viaje.objects.filter(pk=viaje.pk).exists())

    def test_post_con_token_valido_funciona(self):
        viaje = crear_viaje(self.ana)
        pagina = self.cliente.get(reverse("viajes:eliminar", args=[viaje.pk]))
        token = pagina.context["csrf_token"]
        respuesta = self.cliente.post(reverse("viajes:eliminar", args=[viaje.pk]), {"csrfmiddlewaretoken": token})
        self.assertEqual(respuesta.status_code, 302)
        self.assertFalse(Viaje.objects.filter(pk=viaje.pk).exists())

    def test_login_sin_token_es_rechazado(self):
        visitante = Client(enforce_csrf_checks=True)
        respuesta = visitante.post(reverse("cuentas:ingresar"), {"username": "ana", "password": CONTRASENA})
        self.assertEqual(respuesta.status_code, 403)

    def test_formularios_incluyen_token(self):
        for url in (reverse("viajes:crear"), reverse("cuentas:perfil")):
            with self.subTest(url=url):
                self.assertContains(self.cliente.get(url), 'name="csrfmiddlewaretoken"')


class CabecerasTests(TestCase):
    def test_cabeceras_de_seguridad(self):
        respuesta = self.client.get(reverse("core:inicio"))
        self.assertIn("default-src 'self'", respuesta["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", respuesta["Content-Security-Policy"])
        self.assertEqual(respuesta["X-Frame-Options"], "DENY")
        self.assertEqual(respuesta["X-Content-Type-Options"], "nosniff")
        self.assertIn("camera=()", respuesta["Permissions-Policy"])

    def test_cookie_csrf_estricta(self):
        respuesta = self.client.get(reverse("cuentas:ingresar"))
        cookie = respuesta.cookies["csrftoken"]
        self.assertEqual(cookie["samesite"], "Strict")
        self.assertTrue(cookie["httponly"])


class SesionTests(TestCase):
    def test_logout_solo_por_post(self):
        crear_usuario("ana")
        self.client.login(username="ana", password=CONTRASENA)
        self.assertEqual(self.client.get(reverse("cuentas:salir")).status_code, 405)
        respuesta = self.client.post(reverse("cuentas:salir"))
        self.assertRedirects(respuesta, reverse("core:inicio"))
        self.assertNotIn("_auth_user_id", self.client.session)


class EscapeHtmlTests(TestCase):
    def test_el_contenido_se_muestra_escapado(self):
        """Aunque llegara HTML a la base de datos, la plantilla lo muestra como texto."""
        ana = crear_usuario("ana")
        viaje = crear_viaje(ana, estado=EstadoViaje.EN_PROGRESO, fecha_inicio=hoy() - timedelta(days=1), fecha_fin=None)
        Viaje.objects.filter(pk=viaje.pk).update(notas="<script>alert('xss')</script>")
        self.client.force_login(ana)
        respuesta = self.client.get(viaje.get_absolute_url())
        self.assertNotContains(respuesta, "<script>alert")
        self.assertContains(respuesta, "&lt;script&gt;")
