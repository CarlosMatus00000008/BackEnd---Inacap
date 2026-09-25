"""
Mixins (piezas reutilizables) para las vistas del diario.

La regla de oro de los permisos: cada vista obtiene los datos SIEMPRE filtrando
por el usuario conectado. Si alguien intenta abrir el viaje de otra persona
cambiando el número en la URL, recibe «404 No encontrado» (ni siquiera sabe si existe).
"""

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import DatabaseError, IntegrityError, transaction

from .forms import ViajeForm
from .models import Viaje

logger = logging.getLogger("viajes")


class AccesoMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """
    Exige sesión iniciada + el permiso de Django indicado en «permission_required».
    - Visitante sin sesión → se le envía a iniciar sesión.
    - Usuario conectado sin el permiso → página 403 con una explicación clara.
    """

    permission_denied_message = (
        "Tu cuenta no tiene permiso para realizar esta acción. "
        "Pídele a un administrador que te agregue al grupo «Viajeros»."
    )


class GuardadoSeguroMixin:
    """
    Guarda dentro de una transacción. Si la base de datos falla, el usuario ve
    un mensaje claro (en vez de una página de error) y no pierde lo que escribió.
    """

    mensaje_conflicto = "Los datos entran en conflicto con otro registro. Revísalos e intenta nuevamente."
    mensaje_error_bd = "No pudimos guardar los cambios por un problema con la base de datos. Intenta en unos segundos."

    def form_valid(self, form):
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except IntegrityError:
            logger.warning("Conflicto de integridad al guardar %s", form.__class__.__name__, exc_info=True)
            form.add_error(None, self.mensaje_conflicto)
        except DatabaseError:
            logger.exception("Error de base de datos al guardar %s", form.__class__.__name__)
            form.add_error(None, self.mensaje_error_bd)
        messages.error(self.request, "No se guardaron los cambios. Revisa los mensajes del formulario.")
        return self.form_invalid(form)


class EliminacionSeguraMixin:
    """Elimina dentro de una transacción y avisa claramente si algo falla."""

    def form_valid(self, form):
        try:
            with transaction.atomic():
                return super().form_valid(form)
        except DatabaseError:
            logger.exception("Error de base de datos al eliminar %s", self.object)
            messages.error(
                self.request, "No se pudo eliminar por un problema con la base de datos. Intenta nuevamente."
            )
            return self.render_to_response(self.get_context_data(form=form))


class ViajePropioMixin:
    """Limita la consulta a los viajes del usuario conectado."""

    def get_queryset(self):
        return Viaje.objects.de_usuario(self.request.user).select_related("pais")


class PaginacionTolerante:
    """Si la página pedida no existe (?page=999 o ?page=abc) muestra la más cercana en vez de un error."""

    def paginate_queryset(self, queryset, page_size):
        paginador = self.get_paginator(
            queryset, page_size, orphans=self.get_paginate_orphans(), allow_empty_first_page=True
        )
        pagina = paginador.get_page(self.request.GET.get(self.page_kwarg))
        return paginador, pagina, pagina.object_list, pagina.has_other_pages()


# ---------------------------------------------------------------------------
# Configuración compartida por crear y editar un viaje
# ---------------------------------------------------------------------------
class ViajeFormMixin(GuardadoSeguroMixin, SuccessMessageMixin):
    """Lo común entre crear y editar un viaje: modelo, formulario y plantilla."""

    model = Viaje
    form_class = ViajeForm
    template_name = "viajes/viaje_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["usuario"] = self.request.user
        return kwargs
