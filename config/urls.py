"""Rutas principales del proyecto: cada app define las suyas en su propio urls.py."""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Diario de Viajes · Administración"
admin.site.site_title = "Diario de Viajes"
admin.site.index_title = "Panel de control"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("cuentas/", include("cuentas.urls")),
    path("", include("viajes.urls")),
    path("", include("core.urls")),
]

# Páginas de error personalizadas (se ven cuando DEBUG=False).
handler400 = "core.views.error_400"
handler403 = "core.views.error_403"
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
