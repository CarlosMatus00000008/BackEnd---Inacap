from django.conf import settings


class CabecerasSeguridadMiddleware:
    """
    Agrega cabeceras HTTP de seguridad a todas las respuestas:

    - Content-Security-Policy: el navegador solo ejecuta scripts y estilos
      servidos por este mismo sitio (bloquea código inyectado → XSS).
    - Permissions-Policy: desactiva APIs del navegador que el sitio no usa.
    """

    PERMISOS = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"

    def __init__(self, get_response):
        self.get_response = get_response
        self.prefijo_admin = "/" + settings.ADMIN_URL

    def __call__(self, request):
        response = self.get_response(request)

        # Las páginas de depuración de Django (solo con DEBUG=True) usan estilos
        # en línea; no se les aplica la política para poder leer los errores.
        es_pagina_depuracion = settings.DEBUG and response.status_code in (404, 500)
        if not es_pagina_depuracion:
            politica = (
                settings.CSP_POLITICA_ADMIN if request.path.startswith(self.prefijo_admin) else settings.CSP_POLITICA
            )
            response.headers.setdefault("Content-Security-Policy", politica)

        response.headers.setdefault("Permissions-Policy", self.PERMISOS)
        return response
