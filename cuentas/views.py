from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import CreateView, UpdateView

from core.texto import limpiar_linea
from viajes.models import EstadoViaje

from .forms import CambioContrasenaForm, IngresoForm, PerfilForm, RegistroForm

Usuario = get_user_model()


class IngresarView(auth_views.LoginView):
    """Inicio de sesión (Django ya protege el formulario con CSRF)."""

    template_name = "cuentas/ingresar.html"
    form_class = IngresoForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        nombre = self.request.user.first_name or self.request.user.username
        messages.success(self.request, f"¡Hola, {nombre}! Qué bueno verte de nuevo.")
        return respuesta


class SalirView(auth_views.LogoutView):
    """Cierre de sesión: solo acepta POST (con token CSRF), nunca un simple enlace."""

    def post(self, request, *args, **kwargs):
        respuesta = super().post(request, *args, **kwargs)
        messages.info(request, "Cerraste sesión correctamente. ¡Buen viaje!")
        return respuesta


@method_decorator(login_not_required, name="dispatch")
class RegistroView(SuccessMessageMixin, CreateView):
    template_name = "cuentas/registro.html"
    form_class = RegistroForm
    success_url = reverse_lazy("viajes:lista")
    success_message = "¡Cuenta creada! Ya puedes registrar tu primer viaje."

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("viajes:lista")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        login(self.request, self.object, backend="django.contrib.auth.backends.ModelBackend")
        return respuesta


class PerfilView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    template_name = "cuentas/perfil.html"
    form_class = PerfilForm
    success_url = reverse_lazy("cuentas:perfil")
    success_message = "Tus datos se actualizaron correctamente."

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        usuario = self.request.user
        contexto["resumen"] = usuario.viajes.aggregate(
            total=Count("pk"),
            completados=Count("pk", filter=Q(estado=EstadoViaje.COMPLETADO)),
            planificados=Count("pk", filter=Q(estado=EstadoViaje.PLANIFICADO)),
        )
        contexto["compartidos_conmigo"] = usuario.viajes_compartidos.exclude(usuario=usuario).count()
        contexto["grupos"] = usuario.groups.values_list("name", flat=True)
        return contexto


class BuscarUsuariosView(View):
    """
    Sugerencias para el campo «Compartir con» (lo usa static/js/buscador-usuarios.js).

    GET ?q=ad → {"resultados": [{"usuario": "admin", "nombre": "…"}]}

    Cuida la privacidad: exige sesión y permiso para crear o editar viajes, pide
    al menos 2 letras, devuelve como máximo 8 personas y nunca entrega correos.
    """

    http_method_names = ["get"]
    MINIMO_LETRAS = 2
    MAXIMO_RESULTADOS = 8

    def get(self, request):
        usuario = request.user
        if not (usuario.has_perm("viajes.add_viaje") or usuario.has_perm("viajes.change_viaje")):
            return JsonResponse({"error": "Tu cuenta no puede compartir viajes."}, status=403)

        texto = limpiar_linea(request.GET.get("q", ""))[:150]
        resultados = []
        if len(texto) >= self.MINIMO_LETRAS:
            coincidencias = (
                Usuario.objects.filter(is_active=True)
                .filter(
                    Q(username__istartswith=texto) | Q(first_name__istartswith=texto) | Q(last_name__istartswith=texto)
                )
                .exclude(pk=usuario.pk)
                .order_by(Lower("username"))[: self.MAXIMO_RESULTADOS]
            )
            resultados = [{"usuario": u.username, "nombre": u.get_full_name()} for u in coincidencias]

        respuesta = JsonResponse({"resultados": resultados})
        respuesta["Cache-Control"] = "private, no-store"
        return respuesta


class CambiarContrasenaView(SuccessMessageMixin, auth_views.PasswordChangeView):
    template_name = "cuentas/cambiar_contrasena.html"
    form_class = CambioContrasenaForm
    success_url = reverse_lazy("cuentas:perfil")
    success_message = "Tu contraseña se cambió correctamente."
