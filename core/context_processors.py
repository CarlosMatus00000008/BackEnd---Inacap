from django.conf import settings
from django.utils import timezone


def aplicacion(request):
    """Variables disponibles en todas las plantillas."""
    return {
        "NOMBRE_APP": "Diario de Viajes",
        "ANIO_ACTUAL": timezone.localdate().year,
        "ADMIN_URL": "/" + settings.ADMIN_URL,
    }
