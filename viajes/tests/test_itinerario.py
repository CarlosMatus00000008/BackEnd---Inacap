"""Pruebas del itinerario de un viaje: guardado, validaciones, orden y permisos."""

from datetime import time, timedelta

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from viajes.models import Actividad
from viajes.senales import GRUPO_VIAJEROS

from .utilidades import crear_usuario, crear_viaje


class ItinerarioTests(TestCase):
    def setUp(self):
        self.ana = crear_usuario("ana")
        self.beto = crear_usuario("beto")
        self.viaje = crear_viaje(self.ana)  # Lima, hace 30 a 25 días
        self.url_crear = reverse("viajes:actividad_crear", args=[self.viaje.pk])
        self.client.force_login(self.ana)

    def datos(self, **cambios):
        datos = {
            "titulo": "Tour por el centro histórico",
            "fecha": self.viaje.fecha_inicio + timedelta(days=1),
            "hora": "10:30",
            "lugar": "Plaza de Armas",
        }
        datos.update(cambios)
        return datos

    def actividad(self, titulo="Museo", dias=0, hora=None):
        fecha = self.viaje.fecha_inicio + timedelta(days=dias)
        return Actividad.objects.create(viaje=self.viaje, fecha=fecha, titulo=titulo, hora=hora)

    def test_grupo_viajeros_tiene_permisos_del_itinerario(self):
        permisos = set(Group.objects.get(name=GRUPO_VIAJEROS).permissions.values_list("codename", flat=True))
        self.assertLessEqual({"add_actividad", "change_actividad", "delete_actividad"}, permisos)

    def test_agregar_actividad_la_muestra_en_su_dia(self):
        respuesta = self.client.post(self.url_crear, self.datos())
        self.assertRedirects(respuesta, f"{self.viaje.get_absolute_url()}#itinerario")
        actividad = Actividad.objects.get()
        self.assertEqual((actividad.viaje, actividad.numero_dia, actividad.hora), (self.viaje, 2, time(10, 30)))

        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertContains(detalle, "Día 2")
        self.assertContains(detalle, "Tour por el centro histórico")
        self.assertContains(detalle, "10:30 · Plaza de Armas")

    def test_hora_y_lugar_son_opcionales(self):
        self.client.post(self.url_crear, self.datos(hora="", lugar=""))
        actividad = Actividad.objects.get()
        self.assertIsNone(actividad.hora)
        self.assertEqual(actividad.lugar, "")

    def test_el_dia_debe_estar_dentro_del_viaje(self):
        antes = self.client.post(self.url_crear, self.datos(fecha=self.viaje.fecha_inicio - timedelta(days=1)))
        self.assertContains(antes, "El viaje comienza el")
        despues = self.client.post(self.url_crear, self.datos(fecha=self.viaje.fecha_fin + timedelta(days=1)))
        self.assertContains(despues, "El viaje termina el")
        self.assertFalse(Actividad.objects.exists())

    def test_titulo_sin_letras_no_se_guarda(self):
        respuesta = self.client.post(self.url_crear, self.datos(titulo="1234"))
        self.assertContains(respuesta, "campo--con-error")
        self.assertFalse(Actividad.objects.exists())

    def test_orden_por_dia_y_hora_sin_hora_al_final(self):
        self.actividad("Día 2 temprano", dias=1, hora=time(9))
        self.actividad("Día 1 sin hora")
        self.actividad("Día 1 noche", hora=time(20))
        self.actividad("Día 1 mañana", hora=time(8))
        titulos = list(self.viaje.actividades.values_list("titulo", flat=True))
        self.assertEqual(titulos, ["Día 1 mañana", "Día 1 noche", "Día 1 sin hora", "Día 2 temprano"])

    def test_marcar_y_desmarcar_como_realizada(self):
        actividad = self.actividad()
        url = reverse("viajes:actividad_marcar", args=[self.viaje.pk, actividad.pk])
        self.assertRedirects(self.client.post(url), f"{self.viaje.get_absolute_url()}#itinerario")
        actividad.refresh_from_db()
        self.assertTrue(actividad.realizada)
        self.assertContains(self.client.get(self.viaje.get_absolute_url()), "1 de 1 realizadas")
        self.client.post(url)
        actividad.refresh_from_db()
        self.assertFalse(actividad.realizada)

    def test_marcar_solo_funciona_por_post(self):
        actividad = self.actividad()
        url = reverse("viajes:actividad_marcar", args=[self.viaje.pk, actividad.pk])
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_eliminar_actividad_pide_confirmacion(self):
        actividad = self.actividad()
        url = reverse("viajes:actividad_eliminar", args=[self.viaje.pk, actividad.pk])
        self.assertContains(self.client.get(url), "¿Eliminar «Museo» del itinerario?")
        self.assertTrue(Actividad.objects.exists())
        respuesta = self.client.post(url, follow=True)
        self.assertFalse(Actividad.objects.exists())
        self.assertContains(respuesta, "Eliminaste «Museo» del itinerario.")

    def test_no_se_modifica_el_itinerario_de_viajes_ajenos_ni_compartidos(self):
        viaje_de_beto = crear_viaje(self.beto, destino="Quito")
        viaje_de_beto.compartido_con.add(self.ana)
        actividad = Actividad.objects.create(viaje=viaje_de_beto, fecha=viaje_de_beto.fecha_inicio, titulo="Teleférico")
        args = [viaje_de_beto.pk, actividad.pk]

        crear = self.client.post(reverse("viajes:actividad_crear", args=[viaje_de_beto.pk]), self.datos())
        marcar = self.client.post(reverse("viajes:actividad_marcar", args=args))
        eliminar = self.client.post(reverse("viajes:actividad_eliminar", args=args))
        self.assertEqual({crear.status_code, marcar.status_code, eliminar.status_code}, {404})
        actividad.refresh_from_db()
        self.assertFalse(actividad.realizada)
        self.assertEqual(Actividad.objects.count(), 1)

    def test_no_se_toca_una_actividad_de_otro_viaje_por_la_url(self):
        otro = crear_viaje(self.beto, destino="Quito")
        ajena = Actividad.objects.create(viaje=otro, fecha=otro.fecha_inicio, titulo="Teleférico")
        respuesta = self.client.post(reverse("viajes:actividad_marcar", args=[self.viaje.pk, ajena.pk]))
        self.assertEqual(respuesta.status_code, 404)

    def test_compartido_ve_el_itinerario_sin_botones(self):
        self.actividad()
        self.viaje.compartido_con.add(self.beto)
        self.client.force_login(self.beto)
        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertContains(detalle, "Museo")
        self.assertNotContains(detalle, self.url_crear)
        self.assertNotContains(detalle, "actividad_marcar")
        self.assertNotContains(detalle, "/realizada/")

    def test_usuario_sin_permisos_recibe_403(self):
        self.client.force_login(crear_usuario("carla", viajero=False))
        self.assertEqual(self.client.post(self.url_crear, self.datos()).status_code, 403)

    def test_eliminar_el_viaje_avisa_y_borra_su_itinerario(self):
        self.actividad()
        confirmacion = self.client.get(reverse("viajes:eliminar", args=[self.viaje.pk]))
        self.assertContains(confirmacion, "actividades del itinerario")
        self.client.post(reverse("viajes:eliminar", args=[self.viaje.pk]))
        self.assertFalse(Actividad.objects.exists())
