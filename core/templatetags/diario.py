"""Etiquetas y filtros de plantilla compartidos por todo el sitio."""

from datetime import date, datetime

from django import template
from django.templatetags.static import static
from django.utils import timezone
from django.utils.html import format_html

from core.basedatos import diagnosticar

register = template.Library()


def _con_puntos(numero) -> str:
    """12500 → «12.500» (punto de miles, como se escribe en Chile)."""
    return f"{int(numero):,}".replace(",", ".")


@register.simple_tag
def icono(nombre: str, clase: str = ""):
    """Dibuja un ícono SVG del archivo static/img/iconos.svg. Uso: {% icono "mapa" %}"""
    return format_html(
        '<svg class="icono {}" aria-hidden="true" focusable="false"><use href="{}#{}"></use></svg>',
        clase,
        static("img/iconos.svg"),
        nombre,
    )


@register.filter
def miles(valor):
    """Número con punto de miles: {{ 12500|miles }} → 12.500"""
    if valor in (None, ""):
        return ""
    return _con_puntos(valor)


@register.filter
def dias(numero):
    """3 → «3 días», 1 → «1 día»."""
    if numero in (None, ""):
        return ""
    return "1 día" if int(numero) == 1 else f"{_con_puntos(numero)} días"


@register.filter
def hace(fecha):
    """Tiempo transcurrido en palabras: «hoy», «hace 3 días», «hace 7 meses», «hace 2 años»."""
    if not isinstance(fecha, date):
        return ""
    if isinstance(fecha, datetime):
        fecha = timezone.localtime(fecha).date() if timezone.is_aware(fecha) else fecha.date()
    dias = (timezone.localdate() - fecha).days
    if dias < 0:
        return "mañana" if dias == -1 else f"en {_con_puntos(-dias)} días"
    if dias == 0:
        return "hoy"
    if dias == 1:
        return "ayer"
    if dias < 30:
        return f"hace {dias} días"
    if dias < 365:
        meses = dias // 30
        return f"hace {meses} mes{'es' if meses > 1 else ''}"
    anios = dias // 365
    return f"hace {anios} año{'s' if anios > 1 else ''}"


@register.simple_tag
def estado_base_datos():
    """Diagnóstico rápido de la base de datos (se muestra en el inicio del admin)."""
    return diagnosticar(incluir_migraciones=False)
