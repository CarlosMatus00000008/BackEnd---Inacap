"""Pruebas de la página de estadísticas: cálculos correctos y solo con los viajes propios."""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from viajes.models import Actividad, EstadoViaje, Gasto, Pais

from .utilidades import crear_usuario, crear_viaje, hoy


def pais(codigo):
    return Pais.objects.get(codigo_iso=codigo)


class EstadisticasTests(TestCase):
    def setUp(self):
        self.ana = crear_usuario("ana")
        self.url = reverse("viajes:estadisticas")
        self.client.force_login(self.ana)

        # Dos viajes a Perú (el último hace 30 días), uno a Japón y uno planificado a Italia.
        self.lima = crear_viaje(self.ana)  # 6 días
        crear_viaje(self.ana, destino="Cusco", fecha_inicio=date(2023, 3, 1), fecha_fin=date(2023, 3, 10))  # 10 días
        crear_viaje(
            self.ana,
            destino="Tokio",
            pais=pais("JP"),
            fecha_inicio=date(2024, 5, 1),
            fecha_fin=date(2024, 5, 3),
        )  # 3 días
        crear_viaje(
            self.ana,
            destino="Roma",
            pais=pais("IT"),
            estado=EstadoViaje.PLANIFICADO,
            fecha_inicio=hoy() + timedelta(days=40),
            fecha_fin=None,
        )

    def contexto(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.context

    def test_cifras_generales(self):
        contexto = self.contexto()
        self.assertEqual(contexto["resumen"]["total"], 4)
        self.assertEqual(contexto["paises_visitados"], 2)  # Perú y Japón (Italia está pendiente)
        self.assertEqual(contexto["continentes_visitados"], 2)
        self.assertEqual(contexto["dias_viajados"], 6 + 10 + 3)
        self.assertEqual(contexto["viaje_mas_largo"].destino, "Cusco")

    def test_ultima_vez_que_fui_a_cada_pais(self):
        ultima_vez = list(self.contexto()["ultima_vez"])
        self.assertEqual([p.codigo_iso for p in ultima_vez], ["PE", "JP"])  # del más reciente al más antiguo
        peru = ultima_vez[0]
        self.assertEqual((peru.veces, peru.ultima), (2, self.lima.fecha_inicio))

    def test_viajes_por_anio_y_pendientes(self):
        contexto = self.contexto()
        por_anio = {fila["anio"]: fila["total"] for fila in contexto["por_anio"]}
        self.assertEqual(por_anio[2023], 1)
        self.assertEqual(por_anio[2024], 1)
        self.assertEqual(sum(por_anio.values()), 4)
        self.assertEqual(contexto["proximo_viaje"].destino, "Roma")
        self.assertEqual([p.codigo_iso for p in contexto["paises_pendientes"]], ["IT"])

    def test_gastos_y_actividades(self):
        Gasto.objects.create(viaje=self.lima, descripcion="Hotel", categoria="alojamiento", monto=90000)
        Gasto.objects.create(viaje=self.lima, descripcion="Taxi", categoria="transporte", monto=10000)
        Actividad.objects.create(viaje=self.lima, fecha=self.lima.fecha_inicio, titulo="Museo", realizada=True)
        Actividad.objects.create(viaje=self.lima, fecha=self.lima.fecha_inicio, titulo="Tour")

        contexto = self.contexto()
        self.assertEqual(contexto["total_gastado"], 100000)
        self.assertEqual(contexto["gastos_por_categoria"][0]["total"], 90000)
        self.assertEqual(contexto["actividades"], {"total": 2, "realizadas": 1})
        self.assertContains(self.client.get(self.url), "$100.000")

    def test_no_cuenta_viajes_de_otras_personas_ni_compartidos(self):
        beto = crear_usuario("beto")
        viaje_de_beto = crear_viaje(beto, destino="Quito", pais=pais("EC"))
        viaje_de_beto.compartido_con.add(self.ana)
        Gasto.objects.create(viaje=viaje_de_beto, descripcion="Hotel", monto=50000)

        contexto = self.contexto()
        self.assertEqual(contexto["resumen"]["total"], 4)
        self.assertNotIn("EC", [p.codigo_iso for p in contexto["ultima_vez"]])
        self.assertEqual(contexto["total_gastado"], 0)

    def test_sin_viajes_muestra_mensaje(self):
        self.client.force_login(crear_usuario("nuevo"))
        self.assertContains(self.client.get(self.url), "Aún no hay nada que contar")

    def test_pide_iniciar_sesion(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), f"{reverse('cuentas:ingresar')}?next={self.url}")
