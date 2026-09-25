"""Pruebas de las vistas: CRUD completo, permisos, paginación, filtros y mensajes al usuario."""

from datetime import timedelta

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse

from viajes.models import EstadoViaje, Pais, Viaje

from .utilidades import crear_usuario, crear_viaje, hoy


def mensajes(respuesta):
    return [str(mensaje) for mensaje in get_messages(respuesta.wsgi_request)]


class AccesoTests(TestCase):
    def setUp(self):
        self.ana = crear_usuario("ana")
        self.beto = crear_usuario("beto")
        self.viaje_de_beto = crear_viaje(self.beto, destino="Quito", pais=Pais.objects.get(codigo_iso="EC"))

    def test_visitante_es_enviado_a_iniciar_sesion(self):
        respuesta = self.client.get(reverse("viajes:lista"))
        self.assertRedirects(respuesta, f"{reverse('cuentas:ingresar')}?next={reverse('viajes:lista')}")

    def test_usuario_solo_ve_sus_viajes(self):
        crear_viaje(self.ana, destino="Arequipa")
        self.client.force_login(self.ana)
        respuesta = self.client.get(reverse("viajes:lista"))
        self.assertContains(respuesta, "Arequipa")
        self.assertNotContains(respuesta, "Quito")

    def test_viaje_ajeno_responde_404(self):
        self.client.force_login(self.ana)
        for nombre in ("detalle", "editar", "eliminar"):
            with self.subTest(vista=nombre):
                respuesta = self.client.get(reverse(f"viajes:{nombre}", args=[self.viaje_de_beto.pk]))
                self.assertEqual(respuesta.status_code, 404)

    def test_no_se_puede_eliminar_un_viaje_ajeno(self):
        self.client.force_login(self.ana)
        self.client.post(reverse("viajes:eliminar", args=[self.viaje_de_beto.pk]))
        self.assertTrue(Viaje.objects.filter(pk=self.viaje_de_beto.pk).exists())

    def test_viaje_compartido_se_ve_en_modo_lectura(self):
        self.viaje_de_beto.compartido_con.add(self.ana)
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(reverse("viajes:compartidos")), "Quito")
        detalle = self.client.get(reverse("viajes:detalle", args=[self.viaje_de_beto.pk]))
        self.assertContains(detalle, "modo solo lectura")
        self.assertNotContains(detalle, reverse("viajes:editar", args=[self.viaje_de_beto.pk]))
        self.assertEqual(self.client.get(reverse("viajes:editar", args=[self.viaje_de_beto.pk])).status_code, 404)

    def test_usuario_sin_permisos_recibe_403_con_explicacion(self):
        sin_grupo = crear_usuario("carla", viajero=False)
        self.client.force_login(sin_grupo)
        respuesta = self.client.get(reverse("viajes:crear"))
        self.assertEqual(respuesta.status_code, 403)
        self.assertContains(respuesta, "Viajeros", status_code=403)


class ViajeCrudTests(TestCase):
    def setUp(self):
        self.ana = crear_usuario("ana")
        self.beto = crear_usuario("beto")
        self.client.force_login(self.ana)
        self.peru = Pais.objects.get(codigo_iso="PE")

    def datos(self, **cambios):
        datos = {
            "destino": "Cusco",
            "pais": self.peru.pk,
            "fecha_inicio": (hoy() + timedelta(days=20)).isoformat(),
            "fecha_fin": (hoy() + timedelta(days=27)).isoformat(),
            "estado": EstadoViaje.PLANIFICADO,
            "notas": "",
            "compartir_con": "",
        }
        datos.update(cambios)
        return datos

    def test_create_guarda_y_asigna_el_dueno(self):
        respuesta = self.client.post(reverse("viajes:crear"), self.datos(compartir_con="BETO"), follow=True)
        viaje = Viaje.objects.get(destino="Cusco")
        self.assertEqual(viaje.usuario, self.ana)
        self.assertEqual(list(viaje.compartido_con.all()), [self.beto])
        self.assertRedirects(respuesta, viaje.get_absolute_url())
        self.assertIn("¡Listo! Tu viaje a Cusco quedó registrado.", mensajes(respuesta))

    def test_create_con_datos_invalidos_muestra_errores(self):
        respuesta = self.client.post(reverse("viajes:crear"), self.datos(destino="", fecha_fin=hoy().isoformat()))
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Viaje.objects.exists())
        self.assertContains(respuesta, "Revisa los campos marcados")
        self.assertTrue(respuesta.context["form"].has_error("destino"))
        self.assertTrue(respuesta.context["form"].has_error("fecha_fin"))

    def test_create_rechaza_usuario_inexistente_para_compartir(self):
        respuesta = self.client.post(reverse("viajes:crear"), self.datos(compartir_con="fantasma"))
        self.assertContains(respuesta, "No encontramos estos usuarios: fantasma.")

    def test_create_sanitiza_el_texto(self):
        self.client.post(
            reverse("viajes:crear"), self.datos(destino="  Cusco   <b>Imperial</b> ", notas="<script>x()</script>Hola")
        )
        viaje = Viaje.objects.get()
        self.assertEqual(viaje.destino, "Cusco Imperial")
        self.assertEqual(viaje.notas, "x()Hola")

    def test_update_precarga_y_guarda_cambios(self):
        viaje = crear_viaje(self.ana)
        formulario = self.client.get(reverse("viajes:editar", args=[viaje.pk]))
        self.assertContains(formulario, 'value="Lima"')
        datos = self.datos(
            destino="Lima",
            fecha_inicio=viaje.fecha_inicio.isoformat(),
            fecha_fin=viaje.fecha_fin.isoformat(),
            estado=EstadoViaje.COMPLETADO,
            notas="Ceviche increíble",
            calificacion="5",
            favorito="on",
        )
        respuesta = self.client.post(reverse("viajes:editar", args=[viaje.pk]), datos, follow=True)
        viaje.refresh_from_db()
        self.assertEqual(viaje.notas, "Ceviche increíble")
        self.assertTrue(viaje.favorito)
        self.assertIn("Guardaste los cambios de tu viaje a Lima.", mensajes(respuesta))

    def test_delete_pide_confirmacion_y_elimina(self):
        viaje = crear_viaje(self.ana, notas="Ceviche increíble")
        confirmacion = self.client.get(reverse("viajes:eliminar", args=[viaje.pk]))
        self.assertContains(confirmacion, "no se puede deshacer")
        self.assertContains(confirmacion, "notas")
        self.assertEqual(Viaje.objects.count(), 1)  # con GET solo se pregunta
        respuesta = self.client.post(reverse("viajes:eliminar", args=[viaje.pk]), follow=True)
        self.assertRedirects(respuesta, reverse("viajes:lista"))
        self.assertFalse(Viaje.objects.exists())
        self.assertTrue(any("Eliminaste el viaje a Lima" in texto for texto in mensajes(respuesta)))

    def test_cambio_rapido_de_estado(self):
        viaje = crear_viaje(
            self.ana, estado=EstadoViaje.EN_PROGRESO, fecha_inicio=hoy() - timedelta(days=2), fecha_fin=None
        )
        self.client.post(reverse("viajes:cambiar_estado", args=[viaje.pk]), {"estado": EstadoViaje.COMPLETADO})
        viaje.refresh_from_db()
        self.assertEqual(viaje.estado, EstadoViaje.COMPLETADO)
        self.assertEqual(viaje.fecha_fin, hoy())

    def test_cambio_de_estado_invalido_muestra_mensaje(self):
        viaje = crear_viaje(self.ana)
        respuesta = self.client.post(
            reverse("viajes:cambiar_estado", args=[viaje.pk]), {"estado": EstadoViaje.PLANIFICADO}, follow=True
        )
        viaje.refresh_from_db()
        self.assertEqual(viaje.estado, EstadoViaje.COMPLETADO)
        self.assertTrue(any("No se pudo cambiar el estado" in texto for texto in mensajes(respuesta)))

    def test_cambio_de_estado_no_acepta_get(self):
        viaje = crear_viaje(self.ana)
        self.assertEqual(self.client.get(reverse("viajes:cambiar_estado", args=[viaje.pk])).status_code, 405)

    def test_redireccion_externa_es_ignorada(self):
        viaje = crear_viaje(self.ana, estado=EstadoViaje.EN_PROGRESO, fecha_inicio=hoy(), fecha_fin=None)
        respuesta = self.client.post(
            reverse("viajes:cambiar_estado", args=[viaje.pk]),
            {"estado": EstadoViaje.COMPLETADO, "siguiente": "https://sitio-malicioso.com/"},
        )
        self.assertRedirects(respuesta, viaje.get_absolute_url())


class LineaTiempoTests(TestCase):
    def setUp(self):
        self.ana = crear_usuario("ana")
        self.client.force_login(self.ana)
        for dias in range(12):
            inicio = hoy() - timedelta(days=100 + dias * 40)
            crear_viaje(
                self.ana, destino=f"Destino {chr(65 + dias)}", fecha_inicio=inicio, fecha_fin=inicio + timedelta(days=3)
            )
        crear_viaje(
            self.ana,
            destino="Tokio",
            pais=Pais.objects.get(codigo_iso="JP"),
            estado=EstadoViaje.PLANIFICADO,
            fecha_inicio=hoy() + timedelta(days=30),
            fecha_fin=None,
            favorito=True,
        )

    def test_orden_y_paginacion(self):
        respuesta = self.client.get(reverse("viajes:lista"))
        viajes = list(respuesta.context["viajes"])
        self.assertEqual(len(viajes), 8)
        self.assertEqual(viajes[0].destino, "Tokio")
        fechas = [viaje.fecha_inicio for viaje in viajes]
        self.assertEqual(fechas, sorted(fechas, reverse=True))
        self.assertTrue(respuesta.context["is_paginated"])

    def test_pagina_inexistente_no_rompe(self):
        self.assertEqual(self.client.get(reverse("viajes:lista"), {"page": "999"}).status_code, 200)
        self.assertEqual(self.client.get(reverse("viajes:lista"), {"page": "abc"}).status_code, 200)

    def test_filtros_por_estado_busqueda_y_favoritos(self):
        pendientes = self.client.get(reverse("viajes:lista"), {"estado": "pendientes"})
        self.assertEqual([v.destino for v in pendientes.context["viajes"]], ["Tokio"])
        busqueda = self.client.get(reverse("viajes:lista"), {"q": "japón"})
        self.assertEqual([v.destino for v in busqueda.context["viajes"]], ["Tokio"])
        favoritos = self.client.get(reverse("viajes:lista"), {"favoritos": "on"})
        self.assertEqual(len(favoritos.context["viajes"]), 1)

    def test_colores_por_estado_en_la_linea_de_tiempo(self):
        respuesta = self.client.get(reverse("viajes:lista"))
        self.assertContains(respuesta, "estado--planificado")
        self.assertContains(respuesta, "estado--completado")
        self.assertContains(respuesta, "📋 Planificado")
        self.assertContains(respuesta, "✓ Completado")

    def test_busqueda_con_intento_de_inyeccion_sql(self):
        respuesta = self.client.get(reverse("viajes:lista"), {"q": "' OR 1=1 --"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["viajes"]), 0)
        self.assertEqual(Viaje.objects.count(), 13)
