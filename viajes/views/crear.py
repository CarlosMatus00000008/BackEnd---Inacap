"""
CREATE: crear viajes.

Diferencia clave con UPDATE (editar.py): aquí el objeto AÚN NO EXISTE. La vista
crea una instancia nueva y le asigna el dueño desde la sesión (request.user),
nunca desde el formulario, para que nadie pueda crear datos a nombre de otro.
"""

from django.views.generic import CreateView

from ..mixins import AccesoMixin, ViajeFormMixin
from ..models import EstadoViaje, Viaje


class ViajeCrearView(AccesoMixin, ViajeFormMixin, CreateView):
    permission_required = "viajes.add_viaje"
    success_message = "¡Listo! Tu viaje a %(destino)s quedó registrado."

    def get_initial(self):
        estado = self.request.GET.get("estado")
        return {"estado": estado} if estado in EstadoViaje.values else {}

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # El dueño se asigna aquí (nunca desde el formulario) → nadie puede crear viajes a nombre de otro.
        kwargs["instance"] = Viaje(usuario=self.request.user)
        return kwargs
