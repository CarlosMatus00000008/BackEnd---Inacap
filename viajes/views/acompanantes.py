"""
Acompañantes de un viaje: agregar y eliminar. Solo el dueño del viaje puede hacerlo;
quienes ven el viaje compartido ven el nombre y la relación (sin el correo) en el detalle.
"""

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, DeleteView

from ..forms import AcompananteForm
from ..mixins import AccesoMixin, EliminacionSeguraMixin, GuardadoSeguroMixin, ViajePadrePropioMixin
from ..models import Acompanante


class AcompananteCrearView(AccesoMixin, ViajePadrePropioMixin, GuardadoSeguroMixin, SuccessMessageMixin, CreateView):
    """El formulario se muestra en el detalle del viaje; si tiene errores, se muestra en su propia página."""

    permission_required = "viajes.add_acompanante"
    form_class = AcompananteForm
    template_name = "viajes/acompanante_form.html"
    success_message = "Agregaste a %(nombre)s como acompañante."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Acompanante(viaje=self.viaje)  # el viaje viene de la URL, nunca del formulario
        return kwargs

    def get_success_url(self):
        return f"{self.viaje.get_absolute_url()}#acompanantes"


class AcompananteEliminarView(AccesoMixin, ViajePadrePropioMixin, EliminacionSeguraMixin, DeleteView):
    permission_required = "viajes.delete_acompanante"
    template_name = "viajes/confirmar_eliminar.html"
    pk_url_kwarg = "acompanante_pk"
    context_object_name = "acompanante"

    def get_queryset(self):
        return Acompanante.objects.filter(viaje=self.viaje)

    def get_context_data(self, **kwargs):
        acompanante = self.object
        return super().get_context_data(
            titulo=f"¿Quitar a {acompanante.nombre} de los acompañantes?",
            descripcion=f"{acompanante.get_relacion_display()} · viaje a {self.viaje.destino}",
            volver_a=self.get_success_url(),
            **kwargs,
        )

    def get_success_url(self):
        return f"{self.viaje.get_absolute_url()}#acompanantes"

    def form_valid(self, form):
        nombre = self.object.nombre
        respuesta = super().form_valid(form)
        messages.success(self.request, f"Quitaste a {nombre} de los acompañantes.")
        return respuesta
