"""
DELETE: eliminar viajes.

Con GET se muestra una página de confirmación que explica qué se borrará; solo un
POST (con token CSRF) elimina de verdad. Luego se informa el resultado con un mensaje.
"""

from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import DeleteView

from ..mixins import AccesoMixin, EliminacionSeguraMixin, ViajePropioMixin


class ViajeEliminarView(AccesoMixin, ViajePropioMixin, EliminacionSeguraMixin, DeleteView):
    permission_required = "viajes.delete_viaje"
    template_name = "viajes/confirmar_eliminar.html"
    success_url = reverse_lazy("viajes:lista")

    def get_context_data(self, **kwargs):
        viaje = self.object
        consecuencias = ["notas"] if viaje.notas else []
        return super().get_context_data(
            titulo=f"¿Eliminar el viaje a {viaje.destino}?",
            descripcion=f"{viaje.destino}, {viaje.pais} · {viaje.fecha_inicio:%d-%m-%Y}",
            consecuencias=consecuencias,
            volver_a=viaje.get_absolute_url(),
            **kwargs,
        )

    def form_valid(self, form):
        nombre = str(self.object.destino)
        respuesta = super().form_valid(form)
        messages.success(self.request, f"Eliminaste el viaje a {nombre}.")
        return respuesta
