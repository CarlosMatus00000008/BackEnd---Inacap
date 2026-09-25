from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Piezas compartidas por todo el sitio: seguridad, formularios, errores y utilidades."""

    name = "core"
    verbose_name = "Núcleo del sitio"
