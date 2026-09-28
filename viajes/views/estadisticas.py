"""READ: estadísticas de mis viajes (el cálculo está en viajes/estadisticas.py)."""

from django.views.generic import TemplateView

from .. import estadisticas
from ..mixins import AccesoMixin


class EstadisticasView(AccesoMixin, TemplateView):
    permission_required = "viajes.view_viaje"
    template_name = "viajes/estadisticas.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(**estadisticas.calcular(self.request.user), **kwargs)
