"""
Itinerario de un viaje: agregar actividades, marcarlas como realizadas y eliminarlas.
Solo el dueño del viaje puede hacerlo; quienes ven el viaje compartido lo ven en modo lectura.
"""

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView

from ..forms import ActividadForm
from ..mixins import AccesoMixin, EliminacionSeguraMixin, GuardadoSeguroMixin, ViajePadrePropioMixin
from ..models import Actividad


def dia_sugerido(viaje):
    """Hoy si cae dentro del viaje; si no, su primer día."""
    hoy = timezone.localdate()
    if viaje.fecha_inicio <= hoy and (viaje.fecha_fin is None or hoy <= viaje.fecha_fin):
        return hoy
    return viaje.fecha_inicio


class ItinerarioMixin(AccesoMixin, ViajePadrePropioMixin):
    """El viaje sale de la URL y siempre es del usuario conectado (si no, 404)."""

    def get_success_url(self):
        return f"{self.viaje.get_absolute_url()}#itinerario"


class ActividadCrearView(ItinerarioMixin, GuardadoSeguroMixin, SuccessMessageMixin, CreateView):
    """El formulario se muestra en el detalle del viaje; si tiene errores, se muestra en su propia página."""

    permission_required = "viajes.add_actividad"
    form_class = ActividadForm
    template_name = "viajes/actividad_form.html"
    success_message = "Agregaste «%(titulo)s» al itinerario."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Actividad(viaje=self.viaje)  # el viaje viene de la URL, nunca del formulario
        return kwargs

    def get_initial(self):
        return {"fecha": dia_sugerido(self.viaje)}


class ActividadMarcarView(ItinerarioMixin, View):
    """Marca o desmarca una actividad como realizada (solo por POST, con token CSRF)."""

    permission_required = "viajes.change_actividad"
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        actividad = get_object_or_404(self.viaje.actividades, pk=kwargs["actividad_pk"])
        actividad.realizada = not actividad.realizada
        actividad.save(update_fields=["realizada"])
        return redirect(self.get_success_url())


class ActividadEliminarView(ItinerarioMixin, EliminacionSeguraMixin, DeleteView):
    permission_required = "viajes.delete_actividad"
    template_name = "viajes/confirmar_eliminar.html"
    pk_url_kwarg = "actividad_pk"

    def get_queryset(self):
        return self.viaje.actividades.all()

    def get_context_data(self, **kwargs):
        actividad = self.object
        detalle = f"Día {actividad.numero_dia} · {actividad.fecha:%d-%m-%Y}"
        if actividad.hora:
            detalle += f" · {actividad.hora:%H:%M}"
        return super().get_context_data(
            titulo=f"¿Eliminar «{actividad.titulo}» del itinerario?",
            descripcion=detalle,
            volver_a=self.get_success_url(),
            **kwargs,
        )

    def form_valid(self, form):
        titulo = self.object.titulo
        respuesta = super().form_valid(form)
        messages.success(self.request, f"Eliminaste «{titulo}» del itinerario.")
        return respuesta
