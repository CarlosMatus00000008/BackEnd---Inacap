from django.contrib import admin

from .models import FotoViaje, Mg, PerfilUsuario, Viaje


class FotoViajeInline(admin.TabularInline):
    model = FotoViaje
    extra = 0
    max_num = FotoViaje.MAX_FOTOS_POR_VIAJE


@admin.register(Viaje)
class ViajeAdmin(admin.ModelAdmin):
    list_display = ("destino", "pais", "propietario", "fecha_inicio", "fecha_fin", "estado", "total_mg")
    list_filter = ("estado", "pais", "propietario")
    search_fields = ("destino", "pais", "propietario__username")
    ordering = ("-fecha_inicio",)
    readonly_fields = ("estado", "creado", "actualizado")
    inlines = [FotoViajeInline]


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "puede_crear_viajes", "puede_ver_otros", "fecha_registro")
    list_filter = ("puede_crear_viajes", "puede_ver_otros")
    search_fields = ("usuario__username",)


@admin.register(Mg)
class MgAdmin(admin.ModelAdmin):
    list_display = ("usuario", "viaje", "creado")
    search_fields = ("usuario__username", "viaje__destino")
