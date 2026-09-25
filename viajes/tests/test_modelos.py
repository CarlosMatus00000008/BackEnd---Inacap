"""Pruebas de los modelos: validaciones, restricciones de la base de datos y datos calculados."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from viajes.models import EstadoViaje, Pais, Viaje

from .utilidades import crear_usuario, crear_viaje, hoy


class PaisTests(TestCase):
    def test_paises_cargados_por_migracion(self):
        self.assertGreaterEqual(Pais.objects.count(), 193)
        chile = Pais.objects.get(codigo_iso="CL")
        self.assertEqual(str(chile), "Chile")
        self.assertEqual(chile.bandera, "🇨🇱")


class ViajeValidacionTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario()

    def test_str_y_orden_mas_reciente_primero(self):
        antiguo = crear_viaje(
            self.usuario,
            destino="Cusco",
            fecha_inicio=hoy() - timedelta(days=400),
            fecha_fin=hoy() - timedelta(days=390),
        )
        reciente = crear_viaje(self.usuario)
        self.assertEqual(list(Viaje.objects.all()), [reciente, antiguo])
        self.assertIn("Lima, Perú", str(reciente))

    def test_regreso_no_puede_ser_anterior_al_inicio(self):
        with self.assertRaises(ValidationError) as contexto:
            crear_viaje(self.usuario, fecha_fin=hoy() - timedelta(days=40))
        self.assertIn("fecha_fin", contexto.exception.message_dict)

    def test_completado_requiere_fecha_de_regreso(self):
        with self.assertRaises(ValidationError) as contexto:
            crear_viaje(self.usuario, fecha_fin=None)
        self.assertIn("fecha_fin", contexto.exception.message_dict)

    def test_completado_no_puede_estar_en_el_futuro(self):
        with self.assertRaises(ValidationError) as contexto:
            crear_viaje(self.usuario, fecha_inicio=hoy() + timedelta(days=5), fecha_fin=hoy() + timedelta(days=9))
        self.assertIn("estado", contexto.exception.message_dict)

    def test_planificado_debe_ser_futuro(self):
        with self.assertRaises(ValidationError) as contexto:
            crear_viaje(self.usuario, estado=EstadoViaje.PLANIFICADO)
        self.assertIn("estado", contexto.exception.message_dict)

    def test_no_se_puede_calificar_un_viaje_planificado(self):
        with self.assertRaises(ValidationError) as contexto:
            crear_viaje(
                self.usuario,
                estado=EstadoViaje.PLANIFICADO,
                fecha_inicio=hoy() + timedelta(days=3),
                fecha_fin=None,
                calificacion=5,
            )
        self.assertIn("calificacion", contexto.exception.message_dict)

    def test_solo_un_viaje_en_progreso_por_usuario(self):
        crear_viaje(self.usuario, estado=EstadoViaje.EN_PROGRESO, fecha_inicio=hoy(), fecha_fin=None)
        with self.assertRaises(ValidationError) as contexto:
            crear_viaje(
                self.usuario, destino="Quito", estado=EstadoViaje.EN_PROGRESO, fecha_inicio=hoy(), fecha_fin=None
            )
        self.assertIn("estado", contexto.exception.message_dict)

    def test_destino_rechaza_simbolos_peligrosos(self):
        with self.assertRaises(ValidationError) as contexto:
            crear_viaje(self.usuario, destino="<script>alert(1)</script>")
        self.assertIn("destino", contexto.exception.message_dict)

    def test_restricciones_de_la_base_de_datos(self):
        """Aunque alguien se salte la validación, la base de datos rechaza datos incoherentes."""
        viaje = crear_viaje(self.usuario)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Viaje.objects.filter(pk=viaje.pk).update(fecha_fin=viaje.fecha_inicio - timedelta(days=1))
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Viaje.objects.filter(pk=viaje.pk).update(calificacion=9)


class ViajeCalculosTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario()

    def test_duracion_incluye_dia_de_salida_y_regreso(self):
        viaje = crear_viaje(self.usuario, fecha_inicio=hoy() - timedelta(days=10), fecha_fin=hoy() - timedelta(days=6))
        self.assertEqual(viaje.duracion_dias, 5)

    def test_duracion_de_viaje_en_progreso_sin_regreso(self):
        viaje = crear_viaje(
            self.usuario, estado=EstadoViaje.EN_PROGRESO, fecha_inicio=hoy() - timedelta(days=2), fecha_fin=None
        )
        self.assertEqual(viaje.duracion_dias, 3)

    def test_estado_desactualizado_y_sugerido(self):
        viaje = crear_viaje(
            self.usuario, estado=EstadoViaje.EN_PROGRESO, fecha_inicio=hoy() - timedelta(days=5), fecha_fin=hoy()
        )
        Viaje.objects.filter(pk=viaje.pk).update(fecha_fin=hoy() - timedelta(days=1))
        viaje.refresh_from_db()
        self.assertTrue(viaje.estado_desactualizado)
        self.assertEqual(viaje.estado_sugerido, EstadoViaje.COMPLETADO)

    def test_aplicar_completado_ajusta_regreso_a_hoy(self):
        viaje = crear_viaje(
            self.usuario, estado=EstadoViaje.EN_PROGRESO, fecha_inicio=hoy() - timedelta(days=3), fecha_fin=None
        )
        ajustes = viaje.aplicar_estado(EstadoViaje.COMPLETADO)
        viaje.full_clean()
        self.assertEqual(viaje.fecha_fin, hoy())
        self.assertTrue(ajustes)

    def test_con_resumen_trae_pais_y_dueno_en_una_consulta(self):
        crear_viaje(self.usuario)
        with self.assertNumQueries(1):
            viaje = Viaje.objects.con_resumen().get()
            self.assertEqual((viaje.pais.codigo_iso, viaje.usuario.username), ("PE", "ana"))
