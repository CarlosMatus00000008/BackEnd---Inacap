from django.urls import path

from . import views

urlpatterns = [
    path("", views.lista_viajes, name="lista_viajes"),
    path("registro/", views.registro, name="registro"),
    path("viaje/nuevo/", views.crear_viaje, name="crear_viaje"),
    path("viaje/<int:pk>/", views.detalle_viaje, name="detalle_viaje"),
    path("viaje/<int:pk>/editar/", views.editar_viaje, name="editar_viaje"),
    path("viaje/<int:pk>/eliminar/", views.eliminar_viaje, name="eliminar_viaje"),
    path("foto/<int:foto_id>/eliminar/", views.eliminar_foto, name="eliminar_foto"),
    path("viaje/<int:pk>/mg/", views.toggle_mg, name="toggle_mg"),
    path("perfil/", views.perfil_usuario, name="mi_perfil"),
    path("perfil/<str:username>/", views.perfil_usuario, name="perfil_usuario"),
    path("usuarios/", views.gestion_usuarios, name="gestion_usuarios"),
]
