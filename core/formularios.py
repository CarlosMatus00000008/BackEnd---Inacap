"""
Piezas reutilizables para todos los formularios del sitio.

- RenderizadorFormularios: dibuja los campos con nuestras plantillas
  (templates/formularios/), accesibles y con estilos propios.
- FormularioBase: configuración común (sin «:» en las etiquetas, clases CSS).
- TextoField / TextoLargoField: campos que sanitizan el texto automáticamente.
- FechaInput: selector nativo de fecha del navegador.
"""

from django import forms
from django.forms.renderers import TemplatesSetting

from .texto import limpiar_linea, limpiar_parrafos


class RenderizadorFormularios(TemplatesSetting):
    form_template_name = "formularios/formulario.html"
    field_template_name = "formularios/campo.html"


class FormularioBase:
    """Mixin para Form/ModelForm: etiquetas limpias y clases CSS de estado."""

    required_css_class = "campo--obligatorio"
    error_css_class = "campo--con-error"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)


class TextoField(forms.CharField):
    """Texto de una línea: quita HTML, caracteres invisibles y espacios repetidos."""

    def to_python(self, value):
        valor = super().to_python(value)
        return limpiar_linea(valor) if valor else valor


class TextoLargoField(forms.CharField):
    """Texto de varias líneas (notas, descripciones), sanitizado."""

    widget = forms.Textarea

    def to_python(self, value):
        valor = super().to_python(value)
        return limpiar_parrafos(valor) if valor else valor


class FechaInput(forms.DateInput):
    """<input type="date">: el navegador siempre usa el formato ISO AAAA-MM-DD."""

    input_type = "date"

    def __init__(self, attrs=None):
        super().__init__(attrs=attrs, format="%Y-%m-%d")
