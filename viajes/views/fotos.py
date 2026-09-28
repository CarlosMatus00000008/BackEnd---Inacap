"""
Fotos de un viaje: subir (varias a la vez) y eliminar. Solo el dueño del viaje puede hacerlo.

Las fotos se guardan en el almacenamiento configurado en settings.STORAGES["default"]:
Supabase Storage en producción, o la carpeta media/ en desarrollo.
"""

import logging

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.views.generic import DeleteView, FormView

from ..forms import FotosForm
from ..mixins import AccesoMixin, EliminacionSeguraMixin, ViajePadrePropioMixin
from ..models import FotoViaje

logger = logging.getLogger("viajes")


class FotosSubirView(AccesoMixin, ViajePadrePropioMixin, FormView):
    permission_required = "viajes.add_fotoviaje"
    form_class = FotosForm
    template_name = "viajes/fotos_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["viaje"] = self.viaje
        return kwargs

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            fotos_habilitadas=settings.FOTOS_HABILITADAS, maximo_fotos=FotoViaje.MAXIMO_POR_VIAJE, **kwargs
        )

    def get_success_url(self):
        return f"{self.viaje.get_absolute_url()}#fotos"

    def form_valid(self, form):
        if not settings.FOTOS_HABILITADAS:
            form.add_error(None, "La subida de fotos aún no está configurada en el servidor.")
            return self.form_invalid(form)

        subidas = []
        try:
            with transaction.atomic():
                for archivo in form.cleaned_data["fotos"]:
                    foto = FotoViaje(viaje=self.viaje)
                    foto.imagen.save(archivo.name, archivo, save=False)  # sube el archivo al almacenamiento
                    subidas.append(foto.imagen.name)
                    foto.save()
        except Exception:
            logger.exception("No se pudieron subir las fotos del viaje %s", self.viaje.pk)
            self._borrar_archivos(subidas)
            form.add_error(None, "No pudimos subir las fotos. Intenta nuevamente en unos segundos.")
            return self.form_invalid(form)

        cantidad = len(subidas)
        messages.success(self.request, "Subiste 1 foto." if cantidad == 1 else f"Subiste {cantidad} fotos.")
        return super().form_valid(form)

    @staticmethod
    def _borrar_archivos(nombres):
        """Si algo falla a mitad de camino, no deja archivos huérfanos en el almacenamiento."""
        almacenamiento = FotoViaje._meta.get_field("imagen").storage
        for nombre in nombres:
            try:
                almacenamiento.delete(nombre)
            except Exception:
                logger.exception("No se pudo borrar el archivo huérfano %s", nombre)


class FotoEliminarView(AccesoMixin, ViajePadrePropioMixin, EliminacionSeguraMixin, DeleteView):
    """El archivo se borra del almacenamiento automáticamente (ver senales.borrar_archivo_foto)."""

    permission_required = "viajes.delete_fotoviaje"
    template_name = "viajes/confirmar_eliminar.html"
    pk_url_kwarg = "foto_pk"
    context_object_name = "foto"

    def get_queryset(self):
        return FotoViaje.objects.filter(viaje=self.viaje)

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            titulo="¿Eliminar esta foto?",
            descripcion=f"Viaje a {self.viaje.destino} · subida el {timezone.localtime(self.object.subida):%d-%m-%Y}",
            vista_previa=self.object.imagen.url,
            volver_a=self.get_success_url(),
            **kwargs,
        )

    def get_success_url(self):
        return f"{self.viaje.get_absolute_url()}#fotos"

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, "Eliminaste la foto.")
        return respuesta
