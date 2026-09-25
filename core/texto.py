"""
Sanitización de texto ingresado por usuarios.

Django ya escapa automáticamente todo lo que se muestra en las plantillas, pero
además limpiamos la entrada ANTES de guardarla (defensa en profundidad):
se eliminan etiquetas HTML, caracteres de control invisibles y espacios sobrantes.
"""

import re
import unicodedata

from django.utils.html import strip_tags

_CARACTERES_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f​-‏‪-‮⁦-⁩]")
_ESPACIOS_HORIZONTALES = re.compile(r"[ \t ]+")
_SALTOS_REPETIDOS = re.compile(r"\n{3,}")


def _base(valor: str) -> str:
    texto = unicodedata.normalize("NFC", str(valor))
    texto = strip_tags(texto)
    return _CARACTERES_CONTROL.sub("", texto)


def limpiar_linea(valor: str) -> str:
    """Texto de una sola línea (nombres, títulos, lugares)."""
    return re.sub(r"\s+", " ", _base(valor)).strip()


def limpiar_parrafos(valor: str) -> str:
    """Texto largo (notas, descripciones): conserva saltos de línea simples."""
    texto = _base(valor).replace("\r\n", "\n").replace("\r", "\n")
    lineas = (_ESPACIOS_HORIZONTALES.sub(" ", linea).strip() for linea in texto.split("\n"))
    return _SALTOS_REPETIDOS.sub("\n\n", "\n".join(lineas)).strip()
