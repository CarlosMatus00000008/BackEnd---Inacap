"""Pruebas de «Viajes públicos»: solo lectura, con sesión, y sin cambiar los permisos existentes."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from viajes.models import Acompanante, Gasto, Viaje

from .utilidades import crear_usuario, crear_viaje


class ViajesPublicosTests(TestCase):
    def setUp(self):
        self.ana = crear_usuario("ana")
        self.beto = crear_usuario("beto")
        self.publico = crear_viaje(
            self.beto, destino="Cusco", publico=True, presupuesto=900_000, notas="Machu Picchu al amanecer."
        )
        self.privado = crear_viaje(self.beto, destino="Quito")
        self.lista = reverse("viajes:publicos")
        self.detalle = reverse("viajes:publico_detalle", args=[self.publico.pk])
        self.client.force_login(self.ana)

    def test_un_anonimo_va_al_login(self):
        self.client.logout()
        for url in (self.lista, self.detalle):
            with self.subTest(url=url):
                self.assertRedirects(self.client.get(url), f"{reverse('cuentas:ingresar')}?next={url}")

    def test_la_lista_muestra_solo_los_publicos_de_otros(self):
        crear_viaje(self.ana, destino="Lima", publico=True)  # propio: no aparece
        viajes = [viaje.destino for viaje in self.client.get(self.lista).context["viajes"]]
        self.assertEqual(viajes, ["Cusco"])

    def test_un_viaje_privado_ajeno_da_404(self):
        url = reverse("viajes:publico_detalle", args=[self.privado.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_un_viaje_publico_ajeno_se_ve_sin_edicion_ni_datos_privados(self):
        Gasto.objects.create(viaje=self.publico, descripcion="Hotel carísimo", monto=450_000)
        Acompanante.objects.create(viaje=self.publico, nombre="Camila", email="camila@example.com")
        self.publico.compartido_con.add(crear_usuario("carla"))
        pagina = self.client.get(self.detalle)
        self.assertContains(pagina, "Cusco")
        self.assertContains(pagina, "Machu Picchu al amanecer.")
        self.assertContains(pagina, "puedes verlo, pero no modificarlo")
        # Sin gastos, presupuesto, acompañantes ni compartidos.
        for privado in ("Hotel carísimo", "$900.000", "presupuesto", "Camila", "carla", "Compartido con"):
            self.assertNotContains(pagina, privado)
        # Sin botones de edición ni formularios (el único formulario es «Cerrar sesión» del menú).
        for url in (
            reverse("viajes:editar", args=[self.publico.pk]),
            reverse("viajes:eliminar", args=[self.publico.pk]),
            reverse("viajes:gasto_crear", args=[self.publico.pk]),
            reverse("viajes:actividad_crear", args=[self.publico.pk]),
            reverse("viajes:fotos_subir", args=[self.publico.pk]),
        ):
            self.assertNotContains(pagina, url)
        self.assertContains(pagina, "<form", count=1)
        self.assertContains(pagina, reverse("cuentas:salir"))

    def test_post_a_editar_o_eliminar_un_publico_ajeno_da_404(self):
        for nombre in ("editar", "eliminar", "cambiar_estado"):
            with self.subTest(vista=nombre):
                respuesta = self.client.post(
                    reverse(f"viajes:{nombre}", args=[self.publico.pk]), {"estado": "completado"}
                )
                self.assertEqual(respuesta.status_code, 404)
        self.assertTrue(Viaje.objects.filter(pk=self.publico.pk, destino="Cusco").exists())
        self.assertEqual(self.client.post(self.detalle).status_code, 405)  # el detalle público es solo GET

    def test_el_detalle_normal_sigue_igual(self):
        # Publicar no cambia visibles_para(): el detalle normal de un viaje ajeno sigue dando 404.
        self.assertEqual(self.client.get(self.publico.get_absolute_url()).status_code, 404)

    def test_un_viaje_propio_no_se_abre_como_publico(self):
        propio = crear_viaje(self.ana, destino="Lima", publico=True)
        url = reverse("viajes:publico_detalle", args=[propio.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_el_dueno_publica_desde_el_formulario(self):
        viaje = crear_viaje(self.ana, destino="Arequipa")
        datos = {
            "destino": viaje.destino,
            "pais": viaje.pais.pk,
            "fecha_inicio": viaje.fecha_inicio,
            "fecha_fin": viaje.fecha_fin,
            "estado": viaje.estado,
            "publico": "on",
        }
        self.assertContains(self.client.get(reverse("viajes:editar", args=[viaje.pk])), 'name="publico"')
        self.client.post(reverse("viajes:editar", args=[viaje.pk]), datos)
        viaje.refresh_from_db()
        self.assertTrue(viaje.publico)

    def test_enlace_en_el_menu(self):
        self.assertContains(self.client.get(reverse("viajes:lista")), f'href="{self.lista}"')

    def test_columna_y_filtro_en_el_admin(self):
        self.client.force_login(crear_usuario("jefa", viajero=False, is_staff=True, is_superuser=True))
        lista = self.client.get(reverse("admin:viajes_viaje_changelist"), {"publico__exact": "1"})
        self.assertEqual([v.destino for v in lista.context["cl"].result_list], ["Cusco"])
        self.assertContains(lista, "column-publico")

    def test_cargar_demo_publica_dos_viajes(self):
        call_command("cargar_demo", "--forzar", stdout=StringIO())
        publicos = Viaje.objects.filter(usuario__username__in=["viajero", "pareja"], publico=True)
        self.assertEqual(sorted(publicos.values_list("destino", flat=True)), ["Cusco", "Florianópolis"])
