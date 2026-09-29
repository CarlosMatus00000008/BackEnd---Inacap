"""
Gastos de un viaje: agregar y eliminar. Solo el dueño del viaje puede hacerlo;
quienes ven el viaje compartido ven los gastos en modo lectura (en el detalle).
"""

from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, DeleteView

from core.templatetags.diario import cantidad, miles

from ..forms import GastoForm
from ..mixins import AccesoMixin, EliminacionSeguraMixin, GuardadoSeguroMixin, ViajePadrePropioMixin
from ..models import Gasto


class GastoCrearView(AccesoMixin, ViajePadrePropioMixin, GuardadoSeguroMixin, SuccessMessageMixin, CreateView):
    """El formulario se muestra en el detalle del viaje; si tiene errores, se muestra en su propia página."""

    permission_required = "viajes.add_gasto"
    form_class = GastoForm
    template_name = "viajes/gasto_form.html"
    success_message = "Agregaste el gasto «%(descripcion)s»."

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = Gasto(viaje=self.viaje)  # el viaje viene de la URL, nunca del formulario
        return kwargs

    def get_success_url(self):
        return f"{self.viaje.get_absolute_url()}#gastos"


class GastoEliminarView(AccesoMixin, ViajePadrePropioMixin, EliminacionSeguraMixin, DeleteView):
    permission_required = "viajes.delete_gasto"
    template_name = "viajes/confirmar_eliminar.html"
    pk_url_kwarg = "gasto_pk"
    context_object_name = "gasto"

    def get_queryset(self):
        return Gasto.objects.filter(viaje=self.viaje)

    def get_context_data(self, **kwargs):
        gasto = self.object
        monto = f"${miles(gasto.monto)}"
        if gasto.moneda:
            monto += f" ({cantidad(gasto.monto_moneda)} {gasto.moneda})"
        return super().get_context_data(
            titulo=f"¿Eliminar el gasto «{gasto.descripcion}»?",
            descripcion=f"{gasto.get_categoria_display()} · {monto} · {gasto.fecha:%d-%m-%Y}",
            volver_a=self.get_success_url(),
            **kwargs,
        )

    def get_success_url(self):
        return f"{self.viaje.get_absolute_url()}#gastos"

    def form_valid(self, form):
        descripcion = self.object.descripcion
        respuesta = super().form_valid(form)
        messages.success(self.request, f"Eliminaste el gasto «{descripcion}».")
        return respuesta
