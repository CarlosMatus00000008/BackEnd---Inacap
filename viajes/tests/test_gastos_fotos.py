"""Pruebas de presupuesto, gastos y fotos de un viaje: guardado, validaciones y permisos."""

import shutil
import tempfile
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import Group
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from viajes.models import CategoriaGasto, FotoViaje, Gasto, Pais
from viajes.senales import GRUPO_VIAJEROS

from .utilidades import crear_usuario, crear_viaje, hoy


def imagen(nombre="foto.jpg", tamano=(40, 30), formato="JPEG", exif=None):
    salida = BytesIO()
    opciones = {"exif": exif} if exif is not None else {}
    Image.new("RGB", tamano, "#c2412b").save(salida, formato, **opciones)
    return SimpleUploadedFile(nombre, salida.getvalue(), content_type=f"image/{formato.lower()}")


class GastosTests(TestCase):
    def setUp(self):
        self.ana = crear_usuario("ana")
        self.beto = crear_usuario("beto")
        self.viaje = crear_viaje(self.ana)
        self.client.force_login(self.ana)

    def datos(self, **cambios):
        datos = {
            "descripcion": "Vuelo a Lima",
            "categoria": CategoriaGasto.TRANSPORTE,
            "monto": "25.000",
            "fecha": hoy(),
        }
        datos.update(cambios)
        return datos

    def test_grupo_viajeros_tiene_permisos_de_gastos_y_fotos(self):
        permisos = set(Group.objects.get(name=GRUPO_VIAJEROS).permissions.values_list("codename", flat=True))
        self.assertLessEqual({"add_gasto", "delete_gasto", "add_fotoviaje", "delete_fotoviaje"}, permisos)

    def test_agregar_gasto_queda_asociado_al_viaje(self):
        respuesta = self.client.post(reverse("viajes:gasto_crear", args=[self.viaje.pk]), self.datos())
        self.assertRedirects(respuesta, f"{self.viaje.get_absolute_url()}#gastos")
        gasto = Gasto.objects.get()
        self.assertEqual((gasto.viaje, gasto.monto), (self.viaje, 25000))
        self.assertContains(self.client.get(self.viaje.get_absolute_url()), "$25.000")

    def test_monto_en_pesos_con_decimales_se_rechaza(self):
        """«25.000,50» no debe guardarse como 2.500.050: los pesos van sin decimales."""
        respuesta = self.client.post(reverse("viajes:gasto_crear", args=[self.viaje.pk]), self.datos(monto="25.000,50"))
        self.assertContains(respuesta, "Los montos en pesos chilenos van sin decimales.")
        self.assertFalse(Gasto.objects.exists())

    def test_los_montos_se_escriben_con_punto_de_miles(self):
        """Los campos de monto llevan la marca que usa static/js/montos.js para poner los puntos solos."""
        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertContains(detalle, "js/montos.js")
        self.assertContains(detalle, 'name="monto" inputmode="numeric" autocomplete="off" data-monto="entero"')
        self.assertContains(detalle, 'data-monto="decimal"')
        formulario_viaje = self.client.get(reverse("viajes:editar", args=[self.viaje.pk]))
        self.assertContains(formulario_viaje, 'data-monto="entero"')

    def test_monto_invalido_muestra_error_y_no_guarda(self):
        respuesta = self.client.post(reverse("viajes:gasto_crear", args=[self.viaje.pk]), self.datos(monto="0"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "campo--con-error")
        self.assertFalse(Gasto.objects.exists())

    def test_no_se_agregan_gastos_a_viajes_ajenos_ni_compartidos(self):
        viaje_de_beto = crear_viaje(self.beto, destino="Quito")
        viaje_de_beto.compartido_con.add(self.ana)
        respuesta = self.client.post(reverse("viajes:gasto_crear", args=[viaje_de_beto.pk]), self.datos())
        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(Gasto.objects.exists())

    def test_compartido_ve_los_gastos_sin_formulario(self):
        Gasto.objects.create(viaje=self.viaje, descripcion="Hotel", categoria="alojamiento", monto=90000)
        self.viaje.compartido_con.add(self.beto)
        self.client.force_login(self.beto)
        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertContains(detalle, "Hotel")
        self.assertNotContains(detalle, reverse("viajes:gasto_crear", args=[self.viaje.pk]))

    def test_eliminar_gasto_pide_confirmacion(self):
        gasto = Gasto.objects.create(viaje=self.viaje, descripcion="Taxi", monto=8000)
        url = reverse("viajes:gasto_eliminar", args=[self.viaje.pk, gasto.pk])
        self.assertContains(self.client.get(url), "¿Eliminar el gasto «Taxi»?")
        self.client.post(url)
        self.assertFalse(Gasto.objects.exists())

    def test_no_se_elimina_un_gasto_de_otro_viaje(self):
        otro = crear_viaje(self.beto, destino="Quito")
        gasto = Gasto.objects.create(viaje=otro, descripcion="Taxi", monto=8000)
        respuesta = self.client.post(reverse("viajes:gasto_eliminar", args=[self.viaje.pk, gasto.pk]))
        self.assertEqual(respuesta.status_code, 404)
        self.assertTrue(Gasto.objects.exists())

    def test_usuario_sin_permisos_recibe_403(self):
        self.client.force_login(crear_usuario("carla", viajero=False))
        respuesta = self.client.post(reverse("viajes:gasto_crear", args=[self.viaje.pk]), self.datos())
        self.assertEqual(respuesta.status_code, 403)


class PresupuestoTests(TestCase):
    def setUp(self):
        self.ana = crear_usuario("ana")
        self.viaje = crear_viaje(self.ana)
        self.client.force_login(self.ana)

    def test_presupuesto_se_guarda_desde_el_formulario_del_viaje(self):
        datos = {
            "destino": self.viaje.destino,
            "pais": self.viaje.pais.pk,
            "fecha_inicio": self.viaje.fecha_inicio,
            "fecha_fin": self.viaje.fecha_fin,
            "estado": self.viaje.estado,
            "presupuesto": "$850.000",
        }
        respuesta = self.client.post(reverse("viajes:editar", args=[self.viaje.pk]), datos)
        self.assertRedirects(respuesta, self.viaje.get_absolute_url())
        self.viaje.refresh_from_db()
        self.assertEqual(self.viaje.presupuesto, 850000)

    def test_detalle_muestra_disponible_y_exceso(self):
        self.viaje.presupuesto = 100000
        self.viaje.save()
        Gasto.objects.create(viaje=self.viaje, descripcion="Hotel", monto=60000)
        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertContains(detalle, "Disponible")
        self.assertContains(detalle, "$40.000")

        Gasto.objects.create(viaje=self.viaje, descripcion="Tour", monto=50000)
        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertContains(detalle, "Te pasaste por")
        self.assertContains(detalle, "$10.000")


class GastosEnOtraMonedaTests(TestCase):
    """Registro de lo pagado en moneda extranjera: el gasto sigue en pesos y la moneda es un dato extra."""

    def setUp(self):
        self.ana = crear_usuario("ana")
        self.viaje = crear_viaje(
            self.ana, destino="Cartagena", pais=Pais.objects.get(codigo_iso="CO"), presupuesto=800_000
        )
        self.client.force_login(self.ana)
        self.url = reverse("viajes:gasto_crear", args=[self.viaje.pk])

    def datos(self, **cambios):
        datos = {
            "descripcion": "Hotel en Getsemaní",
            "categoria": CategoriaGasto.ALOJAMIENTO,
            "monto": "100.000",
            "fecha": hoy(),
            "moneda": "COP",
            "monto_moneda": "450.000",
        }
        datos.update(cambios)
        return datos

    def test_propone_la_moneda_del_pais_del_viaje(self):
        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertContains(detalle, '<option value="COP" selected>Peso colombiano (COP)</option>', html=True)

    def test_guarda_el_monto_en_la_moneda_extranjera(self):
        self.client.post(self.url, self.datos())
        gasto = Gasto.objects.get()
        self.assertEqual((gasto.monto, gasto.moneda, gasto.monto_moneda), (100_000, "COP", Decimal("450000")))

    def test_acepta_decimales_escritos_con_coma_o_punto(self):
        for escrito, esperado in [("12,50", "12.50"), ("1.234,56", "1234.56"), ("99.9", "99.90")]:
            with self.subTest(escrito=escrito):
                self.client.post(self.url, self.datos(moneda="USD", monto_moneda=escrito))
                self.assertEqual(Gasto.objects.latest("creado").monto_moneda, Decimal(esperado))

    def test_sin_monto_en_otra_moneda_queda_solo_en_pesos(self):
        # La moneda viene propuesta en el formulario; si no se escribe el monto, no se guarda.
        self.client.post(self.url, self.datos(monto_moneda=""))
        gasto = Gasto.objects.get()
        self.assertEqual((gasto.moneda, gasto.monto_moneda), ("", None))

    def test_monto_en_otra_moneda_exige_elegir_la_moneda(self):
        respuesta = self.client.post(self.url, self.datos(moneda=""))
        self.assertContains(respuesta, "Elige en qué moneda pagaste.")
        self.assertFalse(Gasto.objects.exists())

    def test_detalle_muestra_lo_gastado_en_cada_moneda(self):
        Gasto.objects.create(viaje=self.viaje, descripcion="Hotel", monto=100_000, moneda="COP", monto_moneda=450_000)
        Gasto.objects.create(viaje=self.viaje, descripcion="Tour", monto=50_000, moneda="COP", monto_moneda=225_000)
        Gasto.objects.create(viaje=self.viaje, descripcion="Vuelo", monto=300_000)
        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertContains(detalle, "<strong>675.000 pesos colombianos</strong>", html=True)
        self.assertContains(detalle, "(≈ $150.000)")
        self.assertContains(detalle, "$1 = 4,50 COP")
        self.assertContains(detalle, "Tu presupuesto equivale a unos 3.600.000 pesos colombianos.")
        self.assertContains(detalle, "$450.000")  # el total y el presupuesto siguen en pesos

    def test_monedas_mas_caras_que_el_peso_muestran_el_cambio_al_reves(self):
        Gasto.objects.create(viaje=self.viaje, descripcion="Cena", monto=47_500, moneda="USD", monto_moneda=50)
        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertContains(detalle, "<strong>50 dólares estadounidenses</strong>", html=True)
        self.assertContains(detalle, "1 USD = $950")

    def test_la_base_de_datos_exige_moneda_y_monto_juntos(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Gasto.objects.create(viaje=self.viaje, descripcion="Taxi", monto=5000, moneda="COP")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Gasto.objects.create(viaje=self.viaje, descripcion="Taxi", monto=5000, monto_moneda=20_000)


class FotosTests(TestCase):
    def setUp(self):
        self.carpeta = tempfile.mkdtemp()
        ajustes = override_settings(
            MEDIA_ROOT=self.carpeta,
            FOTOS_HABILITADAS=True,
            STORAGES={
                "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
            },
        )
        ajustes.enable()
        self.addCleanup(ajustes.disable)
        self.addCleanup(shutil.rmtree, self.carpeta, ignore_errors=True)

        self.ana = crear_usuario("ana")
        self.viaje = crear_viaje(self.ana)
        self.url = reverse("viajes:fotos_subir", args=[self.viaje.pk])
        self.client.force_login(self.ana)

    def test_subir_varias_fotos(self):
        respuesta = self.client.post(self.url, {"fotos": [imagen("a.jpg"), imagen("b.png", formato="PNG")]})
        self.assertRedirects(respuesta, f"{self.viaje.get_absolute_url()}#fotos")
        self.assertEqual(self.viaje.fotos.count(), 2)
        for foto in self.viaje.fotos.all():
            self.assertTrue(default_storage.exists(foto.imagen.name))
            self.assertTrue(foto.imagen.name.startswith(f"viajes/{self.ana.pk}/{self.viaje.pk}/"))
        self.assertContains(self.client.get(self.viaje.get_absolute_url()), 'class="galeria__foto"', count=2)

    def test_el_credito_de_las_fotos_no_se_muestra(self):
        self.client.post(self.url, {"fotos": [imagen("a.jpg"), imagen("b.jpg")]})
        self.viaje.fotos.update(credito="Ana Pérez · CC BY 4.0")
        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertNotContains(detalle, "Ana Pérez")
        self.assertNotContains(detalle, "Créditos de las fotos")

    def test_portada_con_las_fotos_de_fondo(self):
        self.assertNotContains(self.client.get(self.viaje.get_absolute_url()), "data-carrusel")
        self.client.post(self.url, {"fotos": [imagen("a.jpg"), imagen("b.jpg"), imagen("c.jpg")]})
        detalle = self.client.get(self.viaje.get_absolute_url())
        self.assertContains(detalle, "portada-viaje--fotos")
        # La primera se ve de inmediato; el resto se carga a su turno.
        self.assertContains(detalle, 'class="portada-viaje__foto activa" src=', count=1)
        self.assertContains(detalle, 'class="portada-viaje__foto" data-src=', count=2)

    def test_quita_exif_y_achica_fotos_grandes(self):
        exif = Image.Exif()
        exif[0x010F] = "Camara de prueba"  # «Make»: cualquier dato EXIF sirve para la prueba
        self.client.post(self.url, {"fotos": [imagen(tamano=(3000, 1500), exif=exif)]})
        with default_storage.open(FotoViaje.objects.get().imagen.name) as archivo, Image.open(archivo) as guardada:
            self.assertEqual(guardada.size, (2048, 1024))
            self.assertEqual(len(guardada.getexif()), 0)

    def test_acepta_fotos_del_iphone(self):
        """El iPhone guarda sus JPEG con una segunda imagen dentro (formato MPO): también son JPG."""
        salida = BytesIO()
        principal, secundaria = Image.new("RGB", (40, 30), "#c2412b"), Image.new("RGB", (20, 15), "#222")
        principal.save(salida, "MPO", save_all=True, append_images=[secundaria])
        foto = SimpleUploadedFile("IMG_4814.jpeg", salida.getvalue(), content_type="image/jpeg")

        respuesta = self.client.post(self.url, {"fotos": [foto]})
        self.assertRedirects(respuesta, f"{self.viaje.get_absolute_url()}#fotos")
        with default_storage.open(FotoViaje.objects.get().imagen.name) as archivo, Image.open(archivo) as guardada:
            self.assertEqual(guardada.format, "JPEG")

    def test_rechaza_archivos_que_no_son_imagenes(self):
        falso = SimpleUploadedFile("falsa.jpg", b"no soy una imagen", content_type="image/jpeg")
        respuesta = self.client.post(self.url, {"fotos": [falso]})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(FotoViaje.objects.exists())

    @override_settings(FOTO_TAMANO_MAXIMO_MB=0)
    def test_rechaza_fotos_muy_pesadas(self):
        respuesta = self.client.post(self.url, {"fotos": [imagen()]})
        self.assertContains(respuesta, "pesa más de 0 MB")
        self.assertFalse(FotoViaje.objects.exists())

    def test_respeta_el_maximo_por_viaje(self):
        for _ in range(FotoViaje.MAXIMO_POR_VIAJE - 1):
            FotoViaje.objects.create(viaje=self.viaje, imagen=imagen())
        respuesta = self.client.post(self.url, {"fotos": [imagen(), imagen()]})
        self.assertContains(respuesta, "solo puedes subir 1 más")
        self.assertEqual(self.viaje.fotos.count(), FotoViaje.MAXIMO_POR_VIAJE - 1)

    def test_no_se_suben_fotos_a_viajes_ajenos(self):
        viaje_de_beto = crear_viaje(crear_usuario("beto"), destino="Quito")
        respuesta = self.client.post(reverse("viajes:fotos_subir", args=[viaje_de_beto.pk]), {"fotos": [imagen()]})
        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(FotoViaje.objects.exists())

    def test_sin_almacenamiento_configurado_no_se_suben(self):
        with override_settings(FOTOS_HABILITADAS=False):
            respuesta = self.client.post(self.url, {"fotos": [imagen()]})
        self.assertContains(respuesta, "no está configurada")
        self.assertFalse(FotoViaje.objects.exists())

    def test_eliminar_foto_borra_el_archivo(self):
        foto = FotoViaje.objects.create(viaje=self.viaje, imagen=imagen())
        nombre = foto.imagen.name
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("viajes:foto_eliminar", args=[self.viaje.pk, foto.pk]))
        self.assertFalse(FotoViaje.objects.exists())
        self.assertFalse(default_storage.exists(nombre))

    def test_eliminar_el_viaje_borra_sus_fotos(self):
        nombre = FotoViaje.objects.create(viaje=self.viaje, imagen=imagen()).imagen.name
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("viajes:eliminar", args=[self.viaje.pk]))
        self.assertFalse(default_storage.exists(nombre))
