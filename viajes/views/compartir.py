"""
Compartir las fotos de un viaje por WhatsApp con un enlace privado.

- El dueño del viaje crea el enlace desde un modal en la portada del viaje (número, nombre
  del contacto y vigencia): WhatsApp se abre con el mensaje listo (https://wa.me/...).
  En la página «Compartir fotos» ve los enlaces enviados y puede revocarlos.
- Quien abre el enlace ve SOLO las fotos del viaje, sin cuenta y sin el menú del sitio:
  nada de notas, gastos, itinerario ni otros viajes.
- El enlace deja de funcionar cuando vence o cuando el dueño lo revoca.
"""

from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_not_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.cache import add_never_cache_headers
from django.utils.decorators import method_decorator
from django.views.generic import FormView, TemplateView, View

from ..forms import CompartirFotosForm
from ..mixins import AccesoMixin, ViajePadrePropioMixin
from ..models import EnlaceFotos


def enlace_whatsapp(enlace, url) -> str:
    """https://wa.me/56912345678?text=… abre WhatsApp (app o web) con el mensaje escrito."""
    vence = timezone.localtime(enlace.vence)
    saludo = f"¡Hola, {enlace.nombre}!" if enlace.nombre else "¡Hola!"
    mensaje = (
        f"{saludo} Te invito a ver las fotos de mi viaje «{enlace.viaje.destino}» 📷\n{url}\n"
        f"(Puedes verlas hasta el {vence:%d-%m-%Y})"
    )
    return f"https://wa.me/{enlace.telefono.lstrip('+')}?text={quote(mensaje)}"


class CompartirFotosView(AccesoMixin, ViajePadrePropioMixin, FormView):
    permission_required = "viajes.add_enlacefotos"
    form_class = CompartirFotosForm
    template_name = "viajes/compartir_fotos.html"

    def url_propia(self):
        return reverse("viajes:fotos_compartir", args=[self.viaje.pk])

    def get_context_data(self, **kwargs):
        enlaces = self.viaje.enlaces_fotos.vigentes()
        contexto = super().get_context_data(
            tiene_fotos=self.viaje.fotos.exists(), enlaces=enlaces, url_propia=self.url_propia(), **kwargs
        )
        # Recién creado (?nuevo=<id>): se muestra el botón para abrir WhatsApp con el mensaje listo.
        nuevo_pk = self.request.GET.get("nuevo", "")
        nuevo = enlaces.filter(pk=nuevo_pk).first() if nuevo_pk.isdigit() else None
        if nuevo:
            url = self.request.build_absolute_uri(nuevo.get_absolute_url())
            contexto.update(nuevo=nuevo, enlace_url=url, whatsapp=enlace_whatsapp(nuevo, url))
        return contexto

    def form_valid(self, form):
        if not self.viaje.fotos.exists():
            form.add_error(None, "Este viaje todavía no tiene fotos para compartir.")
            return self.form_invalid(form)
        datos = form.cleaned_data
        enlace = EnlaceFotos.crear(self.viaje, datos["numero"], datos["dias"], nombre=datos["nombre"])
        if "abrir_whatsapp" in self.request.POST:  # desde el modal: directo a WhatsApp
            url = self.request.build_absolute_uri(enlace.get_absolute_url())
            return redirect(enlace_whatsapp(enlace, url))
        return redirect(f"{self.url_propia()}?nuevo={enlace.pk}")


class RevocarEnlaceView(AccesoMixin, ViajePadrePropioMixin, View):
    """Solo por POST: el enlace se elimina y quien lo tenga ya no puede ver las fotos."""

    permission_required = "viajes.delete_enlacefotos"
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        enlace = get_object_or_404(EnlaceFotos, pk=kwargs["enlace_pk"], viaje=self.viaje)
        enlace.delete()
        destinatario = enlace.nombre or enlace.telefono
        messages.success(request, f"Revocaste el enlace enviado a {destinatario}. Ya no puede ver las fotos.")
        return redirect("viajes:fotos_compartir", pk=self.viaje.pk)


@method_decorator(login_not_required, name="dispatch")
class FotosPublicasView(TemplateView):
    """
    La página que abre quien recibe el enlace. No pide cuenta: el código de 43 caracteres
    hace de llave. Si no existe, venció o fue revocado → 404 (no se distingue cuál).
    """

    template_name = "viajes/fotos_publicas.html"

    def get(self, request, *args, **kwargs):
        self.enlace = get_object_or_404(
            EnlaceFotos.objects.vigentes().select_related("viaje__pais", "viaje__usuario"), token=kwargs["token"]
        )
        respuesta = super().get(request, *args, **kwargs)
        add_never_cache_headers(respuesta)  # nada queda guardado en cachés intermedias
        respuesta["X-Robots-Tag"] = "noindex, nofollow"  # los buscadores no la indexan
        respuesta["Referrer-Policy"] = "no-referrer"  # el código no viaja a otros sitios
        return respuesta

    def get_context_data(self, **kwargs):
        viaje = self.enlace.viaje
        return super().get_context_data(
            viaje=viaje,
            autor=viaje.usuario.first_name or viaje.usuario.username,
            fotos=list(viaje.fotos.all()),
            vence=self.enlace.vence,
            **kwargs,
        )
