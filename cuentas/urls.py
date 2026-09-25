from django.urls import path

from . import views

app_name = "cuentas"

urlpatterns = [
    path("ingresar/", views.IngresarView.as_view(), name="ingresar"),
    path("salir/", views.SalirView.as_view(), name="salir"),
    path("registro/", views.RegistroView.as_view(), name="registro"),
    path("perfil/", views.PerfilView.as_view(), name="perfil"),
    path("contrasena/", views.CambiarContrasenaView.as_view(), name="cambiar_contrasena"),
    # Sugerencias al compartir un viaje (responde JSON)
    path("usuarios/buscar/", views.BuscarUsuariosView.as_view(), name="buscar_usuarios"),
]
