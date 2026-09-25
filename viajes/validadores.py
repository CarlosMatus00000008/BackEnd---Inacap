"""Validadores reutilizables para los modelos del diario de viajes."""

import re

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

# Letras (con tildes), números, espacios y signos habituales en nombres de lugares:
# «St. Moritz», «Isla de Pascua (Rapa Nui)», «Cusco / Machu Picchu», «L'Aquila».
_PATRON_TEXTO_SEGURO = re.compile(r"^[\w\s.,:;'’()\-/&!?¿¡#+°]+$")


@deconstructible
class ValidadorTextoConLetras:
    """Exige al menos 2 letras y solo caracteres seguros (sin < > { } $ % etc.)."""

    mensaje_simbolos = "Usa solo letras, números, espacios y signos básicos (. , - ' / ( ))."
    mensaje_letras = "Debe contener al menos 2 letras."

    def __call__(self, valor):
        if not _PATRON_TEXTO_SEGURO.match(valor):
            raise ValidationError(self.mensaje_simbolos, code="caracteres_invalidos")
        if sum(caracter.isalpha() for caracter in valor) < 2:
            raise ValidationError(self.mensaje_letras, code="sin_letras")

    def __eq__(self, otro):
        return isinstance(otro, ValidadorTextoConLetras)


validar_texto_con_letras = ValidadorTextoConLetras()
