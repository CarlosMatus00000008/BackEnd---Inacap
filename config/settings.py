"""
Configuración del proyecto «Diario de Viajes».

La clave secreta y el modo DEBUG NO están escritos en el código: se leen desde
variables de entorno (SECRET_KEY, DEBUG, ALLOWED_HOSTS). En desarrollo, si no
defines SECRET_KEY, se genera una clave temporal al iniciar.

Documentación oficial: https://docs.djangoproject.com/es/5.2/ref/settings/
"""

import os
import sys
from pathlib import Path

from django.contrib.messages import constants as mensajes
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

# «python manage.py test» → se usa para ajustar algunas opciones más abajo.
EJECUTANDO_TESTS = len(sys.argv) > 1 and sys.argv[1] == "test"


# ---------------------------------------------------------------------------
# Funciones auxiliares para leer variables de entorno con su tipo correcto
# ---------------------------------------------------------------------------
def env_str(nombre: str, defecto: str = "") -> str:
    return os.environ.get(nombre, defecto).strip()


def env_bool(nombre: str, defecto: bool = False) -> bool:
    valor = os.environ.get(nombre)
    if valor is None or not valor.strip():
        return defecto
    return valor.strip().lower() in {"1", "true", "t", "si", "sí", "yes", "on"}


def env_int(nombre: str, defecto: int) -> int:
    valor = os.environ.get(nombre, "").strip()
    try:
        return int(valor) if valor else defecto
    except ValueError as error:
        raise ImproperlyConfigured(f"La variable {nombre} debe ser un número entero.") from error


def env_lista(nombre: str, defecto: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(nombre, defecto).split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Seguridad básica
# ---------------------------------------------------------------------------
# Desarrollo local por defecto. En un servidor público se define DEBUG=False.
DEBUG = env_bool("DEBUG", True)

SECRET_KEY = env_str("SECRET_KEY")
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured("Falta la variable de entorno SECRET_KEY (obligatoria con DEBUG=False).")
    # Solo en desarrollo: clave aleatoria al iniciar (así ninguna clave queda escrita en el código).
    SECRET_KEY = get_random_secret_key()

ALLOWED_HOSTS = env_lista("ALLOWED_HOSTS", "localhost,127.0.0.1")


# ---------------------------------------------------------------------------
# Aplicaciones
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.forms",  # permite personalizar las plantillas de formularios
    # Apps del proyecto
    "core.apps.CoreConfig",
    "cuentas.apps.CuentasConfig",
    "viajes.apps.ViajesConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Exige iniciar sesión en TODAS las vistas, salvo las marcadas con
    # @login_not_required (inicio, login, registro, estado del servicio).
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.CabecerasSeguridadMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.aplicacion",
            ],
        },
    },
]

# Plantillas propias para dibujar los campos de formulario (templates/formularios/).
FORM_RENDERER = "core.formularios.RenderizadorFormularios"


# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------
# SQLite: un archivo local (db.sqlite3) que no requiere instalar nada.
# Las pruebas usan automáticamente una base temporal en memoria.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# Autenticación y contraseñas
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "cuentas:ingresar"
LOGIN_REDIRECT_URL = "viajes:lista"
LOGOUT_REDIRECT_URL = "core:inicio"

# Ruta del panel de administración (se puede cambiar con la variable ADMIN_URL para ocultarla).
ADMIN_URL = env_str("ADMIN_URL", "admin/").strip("/") + "/"


# ---------------------------------------------------------------------------
# Cookies, CSRF y cabeceras de seguridad
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # la sesión dura 7 días

CSRF_COOKIE_HTTPONLY = True  # JavaScript no puede leer el token
CSRF_COOKIE_SAMESITE = "Strict"  # el navegador no envía la cookie desde otros sitios
CSRF_FAILURE_VIEW = "core.views.csrf_fallido"  # página clara si el token falla

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# En producción (DEBUG=False) se fuerza HTTPS y cookies seguras.
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("COOKIES_SEGURAS", not DEBUG)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_HSTS_SECONDS = env_int("SECURE_HSTS_SECONDS", 0 if DEBUG else 60 * 60 * 24 * 30)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = False
# La precarga de HSTS requiere inscribir el dominio en hstspreload.org; no aplica a este proyecto.
SILENCED_SYSTEM_CHECKS = ["security.W021"]

# Content-Security-Policy: solo se permiten recursos del propio sitio
# (sin scripts ni estilos en línea) → mitiga ataques XSS.
CSP_POLITICA = (
    "default-src 'self'; script-src 'self'; style-src 'self'; "
    "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; "
    "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
)
# El admin de Django usa algunos estilos en línea propios.
CSP_POLITICA_ADMIN = CSP_POLITICA.replace("style-src 'self'", "style-src 'self' 'unsafe-inline'")


# ---------------------------------------------------------------------------
# Idioma y zona horaria
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Archivos estáticos (CSS, JS, íconos)
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"


# ---------------------------------------------------------------------------
# Mensajes (alertas) → clases CSS propias
# ---------------------------------------------------------------------------
MESSAGE_TAGS = {
    mensajes.DEBUG: "info",
    mensajes.INFO: "info",
    mensajes.SUCCESS: "exito",
    mensajes.WARNING: "aviso",
    mensajes.ERROR: "error",
}


# ---------------------------------------------------------------------------
# Registro de eventos (logs) en consola
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"consola": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["consola"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["consola"], "level": env_str("DJANGO_LOG_LEVEL", "INFO"), "propagate": False},
        "viajes": {"handlers": ["consola"], "level": "INFO", "propagate": False},
        "core": {"handlers": ["consola"], "level": "INFO", "propagate": False},
    },
}
if EJECUTANDO_TESTS:
    # Durante las pruebas se ocultan los avisos esperados (404, 403, CSRF…).
    for nombre_logger in ("django", "viajes", "core"):
        LOGGING["loggers"][nombre_logger]["level"] = "CRITICAL"
