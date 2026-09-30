"""Rutas de la app de viajes, agrupadas por operación CRUD."""

from django.urls import path

from .views import compartir, crear, editar, eliminar, estadisticas, fotos, gastos, itinerario, lectura

app_name = "viajes"

urlpatterns = [
    # --- READ: consultar -----------------------------------------------------
    path("viajes/", lectura.LineaTiempoView.as_view(), name="lista"),
    path("viajes/compartidos/", lectura.CompartidosView.as_view(), name="compartidos"),
    path("viajes/<int:pk>/", lectura.ViajeDetalleView.as_view(), name="detalle"),
    path("viajes/estadisticas/", estadisticas.EstadisticasView.as_view(), name="estadisticas"),
    # --- CREATE: crear ------------------------------------------------------
    path("viajes/nuevo/", crear.ViajeCrearView.as_view(), name="crear"),
    # --- UPDATE: editar -----------------------------------------------------
    path("viajes/<int:pk>/editar/", editar.ViajeEditarView.as_view(), name="editar"),
    path("viajes/<int:pk>/estado/", editar.CambiarEstadoView.as_view(), name="cambiar_estado"),
    # --- DELETE: eliminar ---------------------------------------------------
    path("viajes/<int:pk>/eliminar/", eliminar.ViajeEliminarView.as_view(), name="eliminar"),
    # --- Itinerario, gastos y fotos de un viaje (solo el dueño) --------------
    path("viajes/<int:pk>/itinerario/nueva/", itinerario.ActividadCrearView.as_view(), name="actividad_crear"),
    path(
        "viajes/<int:pk>/itinerario/<int:actividad_pk>/realizada/",
        itinerario.ActividadMarcarView.as_view(),
        name="actividad_marcar",
    ),
    path(
        "viajes/<int:pk>/itinerario/<int:actividad_pk>/eliminar/",
        itinerario.ActividadEliminarView.as_view(),
        name="actividad_eliminar",
    ),
    path("viajes/<int:pk>/gastos/nuevo/", gastos.GastoCrearView.as_view(), name="gasto_crear"),
    path("viajes/<int:pk>/gastos/<int:gasto_pk>/eliminar/", gastos.GastoEliminarView.as_view(), name="gasto_eliminar"),
    path("viajes/<int:pk>/fotos/subir/", fotos.FotosSubirView.as_view(), name="fotos_subir"),
    path("viajes/<int:pk>/fotos/<int:foto_pk>/eliminar/", fotos.FotoEliminarView.as_view(), name="foto_eliminar"),
    # --- Compartir las fotos por WhatsApp (enlace privado, solo fotos) --------
    path("viajes/<int:pk>/fotos/compartir/", compartir.CompartirFotosView.as_view(), name="fotos_compartir"),
    path(
        "viajes/<int:pk>/fotos/compartir/<int:enlace_pk>/revocar/",
        compartir.RevocarEnlaceView.as_view(),
        name="fotos_revocar",
    ),
    path("fotos/<slug:token>/", compartir.FotosPublicasView.as_view(), name="fotos_publicas"),
    path("fotos/<slug:token>/portada.jpg", compartir.PortadaEnlaceView.as_view(), name="fotos_portada"),
]
