"""
READ: viajes públicos de otras personas (solo lectura).

Un viaje es público si su dueño marcó «Publicar en Viajes públicos». Estas vistas usan su
propio queryset (Viaje.objects.publicos_de_otros) y NO tocan visibles_para() ni los permisos
del detalle normal: editar, eliminar, gastos, fotos, etc. siguen siendo solo del dueño.
Igual que todo el sitio, piden iniciar sesión (LoginRequiredMiddleware + AccesoMixin).
El detalle público muestra solo portada, notas, itinerario y fotos: sin gastos, presupuesto,
acompañantes ni la lista de con quién se compartió.
"""

from django.views.generic import DetailView, ListView

from ..mixins import AccesoMixin, PaginacionTolerante
from ..models import FotoViaje, Viaje
from .lectura import ViajeDetalleView


class ViajesPublicosView(AccesoMixin, PaginacionTolerante, ListView):
    permission_required = "viajes.view_viaje"
    template_name = "viajes/publicos.html"
    context_object_name = "viajes"
    paginate_by = 8

    def get_queryset(self):
        return Viaje.objects.publicos_de_otros(self.request.user).con_resumen().order_by("-fecha_inicio")


class ViajePublicoDetalleView(AccesoMixin, DetailView):
    """Si el viaje no es público, es propio o no existe → 404 (no se distingue cuál)."""

    permission_required = "viajes.view_viaje"
    template_name = "viajes/viaje_publico.html"
    context_object_name = "viaje"

    def get_queryset(self):
        return Viaje.objects.publicos_de_otros(self.request.user).con_resumen()

    def get_context_data(self, **kwargs):
        viaje = self.object
        return super().get_context_data(
            es_propietario=False,  # las plantillas compartidas ocultan todo lo editable
            fotos=list(viaje.fotos.all()),
            maximo_fotos=FotoViaje.MAXIMO_POR_VIAJE,
            **ViajeDetalleView.itinerario(viaje),
            **kwargs,
        )
