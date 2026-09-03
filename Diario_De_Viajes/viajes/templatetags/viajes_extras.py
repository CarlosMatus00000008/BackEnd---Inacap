import unicodedata

from django import template

register = template.Library()

# Emoji de bandera por país. Es solo un detalle decorativo para la lista y
# el perfil; si el país no está en el diccionario, se usa un globo genérico.
_BANDERAS = {
    "colombia": "🇨🇴", "indonesia": "🇮🇩", "argentina": "🇦🇷", "francia": "🇫🇷",
    "mexico": "🇲🇽", "japon": "🇯🇵", "italia": "🇮🇹", "chile": "🇨🇱", "peru": "🇵🇪",
    "espana": "🇪🇸", "brasil": "🇧🇷", "estados unidos": "🇺🇸", "eeuu": "🇺🇸",
    "canada": "🇨🇦", "alemania": "🇩🇪", "portugal": "🇵🇹", "reino unido": "🇬🇧",
    "inglaterra": "🇬🇧", "tailandia": "🇹🇭", "china": "🇨🇳", "corea del sur": "🇰🇷",
    "vietnam": "🇻🇳", "grecia": "🇬🇷", "egipto": "🇪🇬", "marruecos": "🇲🇦",
    "turquia": "🇹🇷", "paises bajos": "🇳🇱", "holanda": "🇳🇱", "suiza": "🇨🇭",
    "austria": "🇦🇹", "belgica": "🇧🇪", "irlanda": "🇮🇪", "australia": "🇦🇺",
    "nueva zelanda": "🇳🇿", "cuba": "🇨🇺", "ecuador": "🇪🇨", "bolivia": "🇧🇴",
    "uruguay": "🇺🇾", "paraguay": "🇵🇾", "venezuela": "🇻🇪", "panama": "🇵🇦",
    "costa rica": "🇨🇷", "republica dominicana": "🇩🇴", "islandia": "🇮🇸",
    "noruega": "🇳🇴", "suecia": "🇸🇪", "dinamarca": "🇩🇰", "polonia": "🇵🇱",
    "croacia": "🇭🇷", "india": "🇮🇳", "emiratos arabes unidos": "🇦🇪",
    "sudafrica": "🇿🇦", "singapur": "🇸🇬", "malasia": "🇲🇾", "filipinas": "🇵🇭",
}


def _normalizar(texto):
    texto = texto.strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


@register.filter
def bandera(pais):
    """Devuelve el emoji de bandera para un país; 🌍 si no está mapeado."""
    if not pais:
        return "🌍"
    return _BANDERAS.get(_normalizar(pais), "🌍")


# Paleta de colores para los avatares con inicial, elegida para que se vea
# bien tanto en tema claro como oscuro.
_PALETA_AVATAR = [
    "#4361ee", "#3a86ff", "#7209b7", "#e63946", "#2a9d8f",
    "#e76f51", "#457b9d", "#f4a261", "#06923e", "#9d4edd",
]


@register.filter
def color_avatar(username):
    """Color determinístico (siempre el mismo para el mismo usuario)."""
    if not username:
        return _PALETA_AVATAR[0]
    indice = sum(ord(c) for c in username) % len(_PALETA_AVATAR)
    return _PALETA_AVATAR[indice]


@register.filter
def inicial(username):
    return username[0].upper() if username else "?"
