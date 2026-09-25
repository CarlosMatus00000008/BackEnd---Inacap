"""Pruebas de registro, inicio de sesión y perfil."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from viajes.senales import GRUPO_VIAJEROS
from viajes.tests.utilidades import CONTRASENA, crear_usuario

Usuario = get_user_model()


class RegistroTests(TestCase):
    def datos(self, **cambios):
        datos = {
            "username": "camila",
            "first_name": "Camila",
            "email": "Camila@Example.com",
            "password1": "Viajera.Feliz.2026",
            "password2": "Viajera.Feliz.2026",
        }
        datos.update(cambios)
        return datos

    def test_registro_crea_usuario_viajero_e_inicia_sesion(self):
        respuesta = self.client.post(reverse("cuentas:registro"), self.datos())
        self.assertRedirects(respuesta, reverse("viajes:lista"))
        usuario = Usuario.objects.get(username="camila")
        self.assertEqual(usuario.email, "camila@example.com")
        self.assertTrue(usuario.groups.filter(name=GRUPO_VIAJEROS).exists())
        self.assertTrue(usuario.has_perm("viajes.add_viaje"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), usuario.pk)

    def test_correo_duplicado_es_rechazado(self):
        crear_usuario("ana")
        respuesta = self.client.post(reverse("cuentas:registro"), self.datos(email="ANA@example.com"))
        self.assertContains(respuesta, "Ya existe una cuenta con este correo.")

    def test_contrasena_debil_es_rechazada(self):
        respuesta = self.client.post(
            reverse("cuentas:registro"), self.datos(password1="12345678", password2="12345678")
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(username="camila").exists())


class IngresoTests(TestCase):
    def setUp(self):
        crear_usuario("ana")

    def test_ingreso_correcto(self):
        respuesta = self.client.post(
            reverse("cuentas:ingresar"), {"username": "ana", "password": CONTRASENA}, follow=True
        )
        self.assertRedirects(respuesta, reverse("viajes:lista"))
        self.assertContains(respuesta, "Qué bueno verte de nuevo")

    def test_ingreso_incorrecto_muestra_mensaje_claro(self):
        respuesta = self.client.post(reverse("cuentas:ingresar"), {"username": "ana", "password": "mala"})
        self.assertContains(respuesta, "Usuario o contraseña incorrectos")

    def test_usuario_conectado_no_ve_login_ni_registro(self):
        self.client.login(username="ana", password=CONTRASENA)
        self.assertRedirects(self.client.get(reverse("cuentas:ingresar")), reverse("viajes:lista"))
        self.assertRedirects(self.client.get(reverse("cuentas:registro")), reverse("viajes:lista"))


class PerfilTests(TestCase):
    def test_actualizar_datos(self):
        ana = crear_usuario("ana")
        self.client.force_login(ana)
        respuesta = self.client.post(
            reverse("cuentas:perfil"),
            {"first_name": "Ana", "last_name": "Rojas", "email": "ana@example.com"},
            follow=True,
        )
        ana.refresh_from_db()
        self.assertEqual(ana.get_full_name(), "Ana Rojas")
        self.assertContains(respuesta, "Tus datos se actualizaron correctamente.")


class BuscarUsuariosTests(TestCase):
    """Sugerencias del campo «Compartir con»."""

    def setUp(self):
        self.ana = crear_usuario("ana")
        crear_usuario("admin", viajero=False, first_name="Benjamín", is_staff=True, is_superuser=True)
        crear_usuario("adriana", first_name="Adriana", last_name="Soto")
        crear_usuario("beto", first_name="Adolfo")
        crear_usuario("adan_inactivo", is_active=False)
        self.url = reverse("cuentas:buscar_usuarios")
        self.client.force_login(self.ana)

    def buscar(self, texto):
        respuesta = self.client.get(self.url, {"q": texto})
        self.assertEqual(respuesta.status_code, 200)
        return [r["usuario"] for r in respuesta.json()["resultados"]]

    def test_sugiere_por_inicio_del_usuario_o_del_nombre(self):
        # «ad» → admin y adriana (usuario) + beto (su nombre es Adolfo); nunca inactivos.
        self.assertEqual(self.buscar("ad"), ["admin", "adriana", "beto"])
        self.assertEqual(self.buscar("ADM"), ["admin"])

    def test_pide_al_menos_dos_letras_y_no_se_sugiere_a_uno_mismo(self):
        self.assertEqual(self.buscar("a"), [])
        self.assertNotIn("ana", self.buscar("an"))

    def test_no_entrega_correos_y_limita_resultados(self):
        for numero in range(12):
            crear_usuario(f"adicto{numero}")
        respuesta = self.client.get(self.url, {"q": "ad"})
        resultados = respuesta.json()["resultados"]
        self.assertEqual(len(resultados), 8)
        self.assertEqual(set(resultados[0]), {"usuario", "nombre"})
        self.assertNotIn("@", respuesta.content.decode())
        self.assertEqual(respuesta["Cache-Control"], "private, no-store")

    def test_muestra_nombre_completo(self):
        respuesta = self.client.get(self.url, {"q": "adr"})
        self.assertEqual(respuesta.json()["resultados"], [{"usuario": "adriana", "nombre": "Adriana Soto"}])

    def test_exige_sesion_y_permiso(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url, {"q": "ad"}).status_code, 302)
        sin_grupo = crear_usuario("miron", viajero=False)
        self.client.force_login(sin_grupo)
        self.assertEqual(self.client.get(self.url, {"q": "ad"}).status_code, 403)
        self.assertEqual(self.client.post(self.url, {"q": "ad"}).status_code, 405)

    def test_el_formulario_de_viaje_activa_el_buscador(self):
        respuesta = self.client.get(reverse("viajes:crear"))
        self.assertContains(respuesta, f'data-buscar-usuarios="{self.url}"')
        self.assertContains(respuesta, 'data-maximo="10"')
