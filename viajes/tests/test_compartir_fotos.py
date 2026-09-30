"""Pruebas de compartir las fotos de un viaje por WhatsApp con un enlace privado."""

import shutil
import tempfile
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from viajes.models import EnlaceFotos, FotoViaje, Gasto
from viajes.senales import GRUPO_VIAJEROS

from .test_gastos_fotos import imagen
from .utilidades import crear_usuario, crear_viaje


class CompartirFotosTests(TestCase):
    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        ajustes = override_settings(
            MEDIA_ROOT=self.carpeta,
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            },
        )
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        self.addCleanup(shutil.rmtree, self.carpeta, ignore_errors=True)

        self.ana = crear_usuario("ana", first_name="Ana")
        self.beto = crear_usuario("beto")
        self.viaje = crear_viaje(self.ana, notas="Nota secreta del viaje")
        Gasto.objects.create(viaje=self.viaje, descripcion="Hotel carísimo", monto=500_000)
        for _ in range(3):
            FotoViaje.objects.create(viaje=self.viaje, imagen=ContentFile(imagen().read(), name="foto.jpg"))
        self.url = reverse("viajes:fotos_compartir", args=[self.viaje.pk])
        self.client.force_login(self.ana)

    def crear_enlace(self, numero="8765 4321", nombre="Camila", dias=7, **extra):
        return self.client.post(self.url, {"numero": numero, "nombre": nombre, "dias": dias, **extra})

    def test_grupo_viajeros_puede_compartir_y_revocar(self):
        permisos = set(Group.objects.get(name=GRUPO_VIAJEROS).permissions.values_list("codename", flat=True))
        self.assertLessEqual({"add_enlacefotos", "delete_enlacefotos"}, permisos)

    def test_el_boton_aparece_en_la_portada_solo_para_el_dueno(self):
        self.assertContains(self.client.get(self.viaje.get_absolute_url()), self.url)
        self.viaje.compartido_con.add(self.beto)
        self.client.force_login(self.beto)
        self.assertNotContains(self.client.get(self.viaje.get_absolute_url()), self.url)

    def test_crear_enlace_y_abrir_whatsapp_con_el_mensaje(self):
        respuesta = self.crear_enlace()
        enlace = EnlaceFotos.objects.get()
        self.assertRedirects(respuesta, f"{self.url}?nuevo={enlace.pk}")
        self.assertEqual((enlace.telefono, enlace.nombre), ("+56987654321", "Camila"))  # el +56 9 ya viene puesto
        self.assertEqual(len(enlace.token), 43)
        self.assertAlmostEqual(enlace.vence, timezone.now() + timedelta(days=7), delta=timedelta(minutes=1))

        pagina = self.client.get(respuesta.url)
        whatsapp = pagina.context["whatsapp"]
        self.assertTrue(whatsapp.startswith("https://wa.me/56987654321?text="))
        mensaje = parse_qs(urlsplit(whatsapp).query)["text"][0]
        self.assertIn(f"http://testserver/fotos/{enlace.token}/", mensaje)
        self.assertTrue(
            mensaje.startswith(f"¡Hola, Camila! Te invito a ver las fotos de mi viaje «{self.viaje.destino}»")
        )
        self.assertContains(pagina, "Camila · +56 9 8765 4321")

    def test_telefono_invalido_no_crea_enlace(self):
        respuesta = self.crear_enlace(numero="123")
        self.assertContains(respuesta, "Escribe los 8 dígitos que van después del +56 9")
        self.assertFalse(EnlaceFotos.objects.exists())

    def test_acepta_el_numero_completo_pegado(self):
        for escrito in ("+56 9 8765 4321", "9 8765 4321", "87654321"):
            with self.subTest(escrito=escrito):
                self.crear_enlace(numero=escrito)
                self.assertEqual(EnlaceFotos.objects.latest("creado").telefono, "+56987654321")

    def test_el_modal_del_viaje_va_directo_a_whatsapp(self):
        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertContains(detalle, 'id="dialogo-compartir"')
        self.assertContains(detalle, 'data-abrir-dialogo="dialogo-compartir"')
        self.assertContains(detalle, "Enviar por WhatsApp")
        respuesta = self.crear_enlace(abrir_whatsapp="1")
        self.assertTrue(respuesta.url.startswith("https://wa.me/56987654321?text="))
        self.assertEqual(EnlaceFotos.objects.get().nombre, "Camila")

    def test_viaje_sin_fotos_no_se_comparte(self):
        self.viaje.fotos.all().delete()
        self.assertContains(self.client.get(self.url), "todavía no tiene fotos")
        self.crear_enlace()
        self.assertFalse(EnlaceFotos.objects.exists())

    def test_la_pagina_publica_muestra_solo_las_fotos_y_sin_cuenta(self):
        self.crear_enlace()
        enlace = EnlaceFotos.objects.get()
        self.client.logout()
        respuesta = self.client.get(enlace.get_absolute_url())
        self.assertContains(respuesta, 'class="galeria__foto"', count=3)
        self.assertContains(respuesta, "Ana te compartió 3 fotos")
        # Nada del resto del viaje ni enlaces al sitio (las fotos sí viven en media/viajes/…).
        editar = reverse("viajes:editar", args=[self.viaje.pk])
        for privado in ("Nota secreta del viaje", "Hotel carísimo", f'href="{reverse("viajes:lista")}"', editar):
            self.assertNotContains(respuesta, privado)
        self.assertEqual(respuesta["X-Robots-Tag"], "noindex, nofollow")
        self.assertEqual(respuesta["Referrer-Policy"], "no-referrer")
        self.assertIn("no-store", respuesta["Cache-Control"])

    def test_enlaces_vencidos_revocados_o_inventados_dan_404(self):
        self.crear_enlace()
        enlace = EnlaceFotos.objects.get()
        self.client.logout()
        self.assertEqual(self.client.get(reverse("viajes:fotos_publicas", args=["inventado"])).status_code, 404)

        EnlaceFotos.objects.filter(pk=enlace.pk).update(vence=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get(enlace.get_absolute_url()).status_code, 404)

        EnlaceFotos.objects.filter(pk=enlace.pk).update(vence=timezone.now() + timedelta(days=1))
        self.client.force_login(self.ana)
        self.client.post(reverse("viajes:fotos_revocar", args=[self.viaje.pk, enlace.pk]))
        self.assertFalse(EnlaceFotos.objects.exists())
        self.assertEqual(self.client.get(enlace.get_absolute_url()).status_code, 404)

    def test_nadie_mas_comparte_ni_revoca_mis_enlaces(self):
        self.crear_enlace()
        enlace = EnlaceFotos.objects.get()
        self.viaje.compartido_con.add(self.beto)  # aunque vea el viaje, es de solo lectura
        self.client.force_login(self.beto)
        self.assertEqual(self.crear_enlace().status_code, 404)
        revocar = reverse("viajes:fotos_revocar", args=[self.viaje.pk, enlace.pk])
        self.assertEqual(self.client.post(revocar).status_code, 404)
        self.assertEqual(EnlaceFotos.objects.count(), 1)

    def test_revocar_solo_por_post(self):
        self.crear_enlace()
        enlace = EnlaceFotos.objects.get()
        revocar = reverse("viajes:fotos_revocar", args=[self.viaje.pk, enlace.pk])
        self.assertEqual(self.client.get(revocar).status_code, 405)
        self.assertTrue(EnlaceFotos.objects.exists())
