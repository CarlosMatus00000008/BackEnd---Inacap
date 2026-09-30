"""Pruebas de los acompañantes de un viaje: guardado, validaciones, permisos y privacidad del correo."""

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from viajes.models import Acompanante, RelacionAcompanante
from viajes.senales import GRUPO_VIAJEROS

from .utilidades import crear_usuario, crear_viaje


class AcompanantesTests(TestCase):
    def setUp(self):
        self.ana = crear_usuario("ana")
        self.beto = crear_usuario("beto")
        self.viaje = crear_viaje(self.ana)
        self.url = reverse("viajes:acompanante_crear", args=[self.viaje.pk])
        self.client.force_login(self.ana)

    def datos(self, **cambios):
        datos = {"nombre": "Camila", "relacion": RelacionAcompanante.PAREJA, "email": "camila@example.com"}
        datos.update(cambios)
        return datos

    def test_grupo_viajeros_tiene_permisos_de_acompanantes(self):
        permisos = set(Group.objects.get(name=GRUPO_VIAJEROS).permissions.values_list("codename", flat=True))
        self.assertLessEqual({"add_acompanante", "delete_acompanante"}, permisos)

    def test_agregar_acompanante_queda_asociado_al_viaje(self):
        respuesta = self.client.post(self.url, self.datos())
        self.assertRedirects(respuesta, f"{self.viaje.get_absolute_url()}#acompanantes")
        acompanante = Acompanante.objects.get()
        self.assertEqual((acompanante.viaje, acompanante.nombre), (self.viaje, "Camila"))
        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertContains(detalle, "Camila")
        self.assertContains(detalle, "camila@example.com")  # el dueño ve el correo

    def test_el_correo_es_opcional(self):
        self.client.post(self.url, self.datos(email=""))
        self.assertEqual(Acompanante.objects.get().email, "")

    def test_datos_invalidos_no_se_guardan(self):
        for cambios in ({"nombre": "12345"}, {"email": "no-es-un-correo"}, {"relacion": "vecino"}):
            with self.subTest(cambios=cambios):
                respuesta = self.client.post(self.url, self.datos(**cambios))
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, "campo--con-error")
        self.assertFalse(Acompanante.objects.exists())

    def test_eliminar_pide_confirmacion(self):
        acompanante = Acompanante.objects.create(viaje=self.viaje, nombre="Camila")
        url = reverse("viajes:acompanante_eliminar", args=[self.viaje.pk, acompanante.pk])
        self.assertContains(self.client.get(url), "¿Quitar a Camila de los acompañantes?")
        self.client.post(url)
        self.assertFalse(Acompanante.objects.exists())

    def test_compartido_ve_nombre_y_relacion_sin_correo_ni_formulario(self):
        Acompanante.objects.create(viaje=self.viaje, nombre="Camila", relacion="pareja", email="camila@example.com")
        self.viaje.compartido_con.add(self.beto)
        self.client.force_login(self.beto)
        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertContains(detalle, "Camila")
        self.assertContains(detalle, "Pareja")
        self.assertNotContains(detalle, "camila@example.com")
        self.assertNotContains(detalle, self.url)

    def test_nadie_mas_agrega_ni_quita_acompanantes(self):
        acompanante = Acompanante.objects.create(viaje=self.viaje, nombre="Camila")
        self.viaje.compartido_con.add(self.beto)  # aunque lo vea compartido, es de solo lectura
        self.client.force_login(self.beto)
        self.assertEqual(self.client.post(self.url, self.datos(nombre="Intruso")).status_code, 404)
        eliminar = reverse("viajes:acompanante_eliminar", args=[self.viaje.pk, acompanante.pk])
        self.assertEqual(self.client.post(eliminar).status_code, 404)
        self.assertEqual(list(Acompanante.objects.values_list("nombre", flat=True)), ["Camila"])

    def test_no_se_elimina_un_acompanante_de_otro_viaje(self):
        otro_viaje = crear_viaje(self.ana, destino="Cusco")
        acompanante = Acompanante.objects.create(viaje=otro_viaje, nombre="Camila")
        url = reverse("viajes:acompanante_eliminar", args=[self.viaje.pk, acompanante.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        self.assertTrue(Acompanante.objects.exists())

    def test_inline_en_el_admin_de_viaje(self):
        Acompanante.objects.create(viaje=self.viaje, nombre="Camila")
        self.client.force_login(crear_usuario("jefa", viajero=False, is_staff=True, is_superuser=True))
        respuesta = self.client.get(reverse("admin:viajes_viaje_change", args=[self.viaje.pk]))
        self.assertContains(respuesta, 'name="acompanantes-TOTAL_FORMS"')
        self.assertContains(respuesta, 'value="Camila"')
