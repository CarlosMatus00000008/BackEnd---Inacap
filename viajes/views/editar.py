"""
UPDATE: editar viajes y cambiar su estado con un botón.

Diferencia clave con CREATE (crear.py): aquí el objeto YA EXISTE. La vista lo busca
solo entre los datos del usuario conectado (si es ajeno responde 404), precarga el
formulario con sus valores actuales y vuelve a validarlo completo antes de guardar.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import UpdateView

from ..forms import CambiarEstadoForm
from ..mixins import AccesoMixin, ViajeFormMixin, ViajePropioMixin


class ViajeEditarView(AccesoMixin, ViajePropioMixin, ViajeFormMixin, UpdateView):
    permission_required = "viajes.change_viaje"
    success_message = "Guardaste los cambios de tu viaje a %(destino)s."


class CambiarEstadoView(AccesoMixin, ViajePropioMixin, View):
    """Cambio rápido de estado con un botón (solo POST, protegido con CSRF)."""

    permission_required = "viajes.change_viaje"
    http_method_names = ["post"]

    def post(self, request, pk):
        viaje = get_object_or_404(self.get_queryset(), pk=pk)
        formulario = CambiarEstadoForm(request.POST)
        if not formulario.is_valid():
            messages.error(request, "El estado elegido no es válido.")
            return redirect(viaje)

        ajustes = viaje.aplicar_estado(formulario.cleaned_data["estado"])
        try:
            viaje.full_clean()
        except ValidationError as error:
            messages.error(request, "No se pudo cambiar el estado: " + " ".join(error.messages))
        else:
            viaje.save(update_fields=["estado", "fecha_fin", "actualizado"])
            detalle = f" ({', '.join(ajustes)})" if ajustes else ""
            messages.success(
                request, f"{viaje.destino} ahora está «{viaje.get_estado_display()}» {viaje.icono_estado}{detalle}."
            )

        # Solo se vuelve a direcciones de este mismo sitio (evita redirecciones maliciosas).
        destino = request.POST.get("siguiente", "")
        if url_has_allowed_host_and_scheme(
            destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        ):
            return redirect(destino)
        return redirect(viaje)
