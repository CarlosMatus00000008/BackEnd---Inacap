"""Rutas de la app de viajes, agrupadas por operación CRUD."""

from django.urls import path

from .views import crear, editar, eliminar, lectura

app_name = "viajes"

urlpatterns = [
    # --- READ: consultar -----------------------------------------------------
    path("viajes/", lectura.LineaTiempoView.as_view(), name="lista"),
    path("viajes/compartidos/", lectura.CompartidosView.as_view(), name="compartidos"),
    path("viajes/<int:pk>/", lectura.ViajeDetalleView.as_view(), name="detalle"),
    # --- CREATE: crear ------------------------------------------------------
    path("viajes/nuevo/", crear.ViajeCrearView.as_view(), name="crear"),
    # --- UPDATE: editar -----------------------------------------------------
    path("viajes/<int:pk>/editar/", editar.ViajeEditarView.as_view(), name="editar"),
    path("viajes/<int:pk>/estado/", editar.CambiarEstadoView.as_view(), name="cambiar_estado"),
    # --- DELETE: eliminar ---------------------------------------------------
    path("viajes/<int:pk>/eliminar/", eliminar.ViajeEliminarView.as_view(), name="eliminar"),
]
