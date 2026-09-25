import logging

from django.contrib.auth.decorators import login_not_required
from django.http import HttpResponseServerError, JsonResponse
from django.shortcuts import redirect, render
from django.template import loader
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .basedatos import diagnosticar

logger = logging.getLogger(__name__)


@login_not_required
@require_GET
def inicio(request):
    """Portada pública. Si el usuario ya inició sesión, va directo a su línea de tiempo."""
    if request.user.is_authenticated:
        return redirect("viajes:lista")
    return render(request, "core/inicio.html")


@login_not_required
@require_GET
@never_cache
def salud(request):
    """
    Estado del servicio en formato JSON: sirve para comprobar que la aplicación
    y la base de datos responden. No expone datos sensibles.
    """
    estado = diagnosticar(incluir_migraciones=False)
    datos = {
        "estado": "ok" if estado.conectada else "error",
        "base_de_datos": {
            "conectada": estado.conectada,
            "motor": estado.motor,
            "latencia_ms": estado.latencia_ms,
        },
    }
    return JsonResponse(datos, status=200 if estado.conectada else 503)


# ---------------------------------------------------------------------------
# Páginas de error con mensajes claros para el usuario
# ---------------------------------------------------------------------------
@login_not_required
def csrf_fallido(request, reason=""):
    logger.warning("Solicitud rechazada por CSRF en %s: %s", request.path, reason)
    return render(request, "403_csrf.html", status=403)


def error_400(request, exception=None):
    return render(request, "400.html", status=400)


def error_403(request, exception=None):
    # Los mensajes de PermissionDenied de este proyecto están pensados para el usuario.
    mensaje = str(exception) if exception else ""
    return render(request, "403.html", {"mensaje": mensaje}, status=403)


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    # Sin contexto de usuario: si la falla viene de la base de datos,
    # esta página igual debe poder mostrarse.
    return HttpResponseServerError(loader.get_template("500.html").render())
