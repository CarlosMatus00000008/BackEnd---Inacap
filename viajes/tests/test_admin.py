"""Pruebas del panel de administración personalizado."""

from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from viajes.admin import ViajeAdmin
from viajes.models import Gasto

from .utilidades import crear_usuario, crear_viaje


class AdminTests(TestCase):
    def setUp(self):
        self.admin = crear_usuario("jefa", viajero=False, is_staff=True, is_superuser=True)
        self.ana = crear_usuario("ana")
        self.viaje = crear_viaje(self.ana)
        self.client.force_login(self.admin)

    def test_listas_con_filtros_y_busqueda(self):
        paginas = [
            reverse("admin:viajes_viaje_changelist"),
            reverse("admin:viajes_viaje_changelist") + "?q=lima&estado__exact=completado&temporalidad=pasado",
            reverse("admin:viajes_viaje_changelist") + "?revisar=si",
            reverse("admin:viajes_pais_changelist") + "?q=chi",
            reverse("admin:auth_user_changelist"),
            reverse("admin:viajes_viaje_change", args=[self.viaje.pk]),
            reverse("admin:viajes_viaje_add"),
            reverse("admin:index"),
        ]
        for url in paginas:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_columnas_de_presupuesto_y_gastos_totales(self):
        self.viaje.presupuesto = 1_500_000
        self.viaje.save()
        Gasto.objects.create(viaje=self.viaje, descripcion="Hotel", monto=300_000)
        Gasto.objects.create(viaje=self.viaje, descripcion="Tour", monto=45_500)
        sin_gastos = crear_viaje(self.ana, destino="Arequipa")
        lista = self.client.get(reverse("admin:viajes_viaje_changelist"))
        self.assertContains(lista, "$1.500.000")
        self.assertContains(lista, "$345.500")  # suma de los dos gastos, sin duplicar filas
        viajes = {viaje.pk: viaje for viaje in lista.context["cl"].result_list}
        self.assertEqual(viajes[self.viaje.pk].total_gastos, 345_500)
        self.assertIsNone(viajes[sin_gastos.pk].total_gastos)  # se muestra «—»

    def test_ordenar_por_gastos_totales(self):
        caro = crear_viaje(self.ana, destino="Cusco")
        Gasto.objects.create(viaje=caro, descripcion="Tren", monto=900_000)
        Gasto.objects.create(viaje=self.viaje, descripcion="Taxi", monto=10_000)
        columna = ViajeAdmin.list_display.index("gastos_totales")
        lista = self.client.get(reverse("admin:viajes_viaje_changelist"), {"o": f"-{columna}"})
        self.assertEqual([v.destino for v in lista.context["cl"].result_list], ["Cusco", "Lima"])

    def test_indice_muestra_estado_de_la_base_de_datos(self):
        self.assertContains(self.client.get(reverse("admin:index")), "Base de datos conectada")

    def test_accion_marcar_favoritos(self):
        self.client.post(
            reverse("admin:viajes_viaje_changelist"),
            {"action": "marcar_favoritos", "_selected_action": [self.viaje.pk]},
        )
        self.viaje.refresh_from_db()
        self.assertTrue(self.viaje.favorito)

    def test_accion_exportar_csv(self):
        respuesta = self.client.post(
            reverse("admin:viajes_viaje_changelist"),
            {"action": "exportar_csv", "_selected_action": [self.viaje.pk]},
        )
        self.assertEqual(respuesta["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("Lima", respuesta.content.decode("utf-8-sig"))

    def test_staff_sin_superusuario_solo_ve_lo_suyo(self):
        staff = crear_usuario("editor", is_staff=True)
        staff.user_permissions.add(*Permission.objects.filter(codename__in=["view_viaje", "change_viaje"]))
        crear_viaje(staff, destino="Trujillo")
        self.client.force_login(staff)
        respuesta = self.client.get(reverse("admin:viajes_viaje_changelist"))
        self.assertContains(respuesta, "Trujillo")
        self.assertNotContains(respuesta, "Lima")
        # El viaje ajeno «no existe» para él: el admin lo redirige al inicio.
        self.assertEqual(self.client.get(reverse("admin:viajes_viaje_change", args=[self.viaje.pk])).status_code, 302)
