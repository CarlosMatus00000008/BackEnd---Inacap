"""Pruebas de presupuesto, gastos y fotos de un viaje: guardado, validaciones y permisos."""

import shutil
import tempfile
from io import BytesIO

from django.contrib.auth.models import Group
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from viajes.models import CategoriaGasto, FotoViaje, Gasto
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

    def test_quita_exif_y_achica_fotos_grandes(self):
        exif = Image.Exif()
        exif[0x010F] = "Camara de prueba"  # «Make»: cualquier dato EXIF sirve para la prueba
        self.client.post(self.url, {"fotos": [imagen(tamano=(3000, 1500), exif=exif)]})
        with default_storage.open(FotoViaje.objects.get().imagen.name) as archivo, Image.open(archivo) as guardada:
            self.assertEqual(guardada.size, (2048, 1024))
            self.assertEqual(len(guardada.getexif()), 0)

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
