"""
Panel de administración de los viajes.

- Columnas personalizadas (bandera, estado con color, duración, estrellas).
- Filtros múltiples, incluidos filtros propios (temporalidad y estado por revisar).
- Búsqueda y jerarquía por fechas.
- Acciones masivas (marcar completados/favoritos, exportar a CSV para Excel).
- Un miembro del staff que NO es superusuario solo ve y edita sus propios viajes.
"""

import csv

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.html import format_html

from .models import EstadoViaje, Pais, Viaje


# ---------------------------------------------------------------------------
# Piezas comunes
# ---------------------------------------------------------------------------
class PropietarioAdminMixin:
    """El superusuario ve todo; el resto del staff, solo lo suyo."""

    campo_propietario = "usuario"

    def get_queryset(self, request):
        consulta = super().get_queryset(request)
        if request.user.is_superuser:
            return consulta
        return consulta.filter(**{self.campo_propietario: request.user})


class TemporalidadFilter(admin.SimpleListFilter):
    title = "temporalidad"
    parameter_name = "temporalidad"

    def lookups(self, request, model_admin):
        return [
            ("pasado", "Pasado (ya terminó)"),
            ("presente", "Presente (ocurre hoy)"),
            ("futuro", "Futuro (aún no comienza)"),
        ]

    def queryset(self, request, queryset):
        hoy = timezone.localdate()
        match self.value():
            case "pasado":
                return queryset.filter(fecha_fin__lt=hoy)
            case "presente":
                return queryset.filter(Q(fecha_inicio__lte=hoy) & (Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=hoy)))
            case "futuro":
                return queryset.filter(fecha_inicio__gt=hoy)
        return queryset


class EstadoPorRevisarFilter(admin.SimpleListFilter):
    """Viajes cuyo estado quedó desfasado con el paso del tiempo."""

    title = "estado por revisar"
    parameter_name = "revisar"

    def lookups(self, request, model_admin):
        return [("si", "Necesitan actualizar su estado")]

    def queryset(self, request, queryset):
        if self.value() != "si":
            return queryset
        hoy = timezone.localdate()
        return queryset.filter(
            Q(estado=EstadoViaje.PLANIFICADO, fecha_inicio__lt=hoy)
            | Q(estado=EstadoViaje.EN_PROGRESO, fecha_fin__lt=hoy)
        )


# ---------------------------------------------------------------------------
# Viaje
# ---------------------------------------------------------------------------
@admin.register(Viaje)
class ViajeAdmin(PropietarioAdminMixin, admin.ModelAdmin):
    list_display = (
        "destino_con_bandera",
        "pais",
        "usuario",
        "fecha_inicio",
        "duracion",
        "estado_con_color",
        "favorito",
        "estrellas",
    )
    list_display_links = ("destino_con_bandera",)
    list_editable = ("favorito",)
    list_filter = (
        "estado",
        TemporalidadFilter,
        EstadoPorRevisarFilter,
        "favorito",
        "pais__continente",
        ("pais", admin.RelatedOnlyFieldListFilter),
        ("usuario", admin.RelatedOnlyFieldListFilter),
    )
    search_fields = ("destino", "pais__nombre", "notas", "usuario__username")
    search_help_text = "Busca por destino, país, notas o nombre de usuario."
    date_hierarchy = "fecha_inicio"
    ordering = ("-fecha_inicio",)
    list_per_page = 20
    list_select_related = ("pais", "usuario")
    show_facets = admin.ShowFacets.ALWAYS
    save_on_top = True
    autocomplete_fields = ("pais",)
    filter_horizontal = ("compartido_con",)
    readonly_fields = ("duracion_texto", "creado", "actualizado")
    actions = ("marcar_completados", "marcar_favoritos", "quitar_favoritos", "exportar_csv")
    fieldsets = (
        ("Destino", {"fields": ("usuario", "destino", "pais")}),
        ("Fechas y estado", {"fields": (("fecha_inicio", "fecha_fin"), "estado", "duracion_texto")}),
        ("Recuerdos", {"fields": ("notas", ("favorito", "calificacion"))}),
        ("Compartir", {"fields": ("compartido_con",), "classes": ("collapse",)}),
        ("Registro", {"fields": (("creado", "actualizado"),), "classes": ("collapse",)}),
    )

    def get_readonly_fields(self, request, obj=None):
        campos = super().get_readonly_fields(request, obj)
        return campos if request.user.is_superuser else (*campos, "usuario")

    def save_model(self, request, obj, form, change):
        if not change and not request.user.is_superuser:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)

    # --- Columnas personalizadas ---
    @admin.display(description="destino", ordering="destino")
    def destino_con_bandera(self, obj):
        return f"{obj.pais.bandera} {obj.destino}"

    @admin.display(description="estado", ordering="estado")
    def estado_con_color(self, obj):
        return format_html(
            '<span class="insignia-estado insignia-estado--{}">{} {}</span>',
            obj.estado,
            obj.icono_estado,
            obj.get_estado_display(),
        )

    @admin.display(description="duración")
    def duracion(self, obj):
        return f"{obj.duracion_dias} días" if obj.duracion_dias else "—"

    @admin.display(description="duración aproximada")
    def duracion_texto(self, obj):
        if obj is None or not obj.pk:
            return "Se calcula al guardar."
        return self.duracion(obj)

    @admin.display(description="calificación", ordering="calificacion")
    def estrellas(self, obj):
        if not obj.calificacion:
            return "—"
        return "★" * obj.calificacion + "☆" * (5 - obj.calificacion)

    # --- Acciones masivas ---
    @admin.action(description="✓ Marcar como completados", permissions=["change"])
    def marcar_completados(self, request, queryset):
        actualizados = 0
        for viaje in queryset.select_related("pais"):
            viaje.aplicar_estado(EstadoViaje.COMPLETADO)
            try:
                viaje.full_clean()
            except ValidationError as error:
                self.message_user(request, f"{viaje.destino}: {' '.join(error.messages)}", messages.WARNING)
                continue
            viaje.save()
            actualizados += 1
        if actualizados:
            self.message_user(request, f"{actualizados} viaje(s) marcados como completados.", messages.SUCCESS)

    @admin.action(description="★ Marcar como favoritos", permissions=["change"])
    def marcar_favoritos(self, request, queryset):
        cantidad = queryset.update(favorito=True)
        self.message_user(request, f"{cantidad} viaje(s) marcados como favoritos.", messages.SUCCESS)

    @admin.action(description="☆ Quitar de favoritos", permissions=["change"])
    def quitar_favoritos(self, request, queryset):
        cantidad = queryset.update(favorito=False)
        self.message_user(request, f"{cantidad} viaje(s) quitados de favoritos.", messages.SUCCESS)

    @admin.action(description="⬇ Exportar seleccionados a CSV (Excel)", permissions=["view"])
    def exportar_csv(self, request, queryset):
        respuesta = HttpResponse(content_type="text/csv; charset=utf-8")
        respuesta["Content-Disposition"] = f'attachment; filename="viajes_{timezone.localdate():%Y%m%d}.csv"'
        respuesta.write("﻿")  # BOM: Excel reconoce las tildes correctamente
        escritor = csv.writer(respuesta, delimiter=";")
        escritor.writerow(
            ["Destino", "País", "Estado", "Inicio", "Regreso", "Días", "Favorito", "Calificación", "Usuario"]
        )
        for viaje in queryset.select_related("pais", "usuario"):
            escritor.writerow(
                [
                    viaje.destino,
                    viaje.pais.nombre,
                    viaje.get_estado_display(),
                    f"{viaje.fecha_inicio:%d-%m-%Y}",
                    f"{viaje.fecha_fin:%d-%m-%Y}" if viaje.fecha_fin else "",
                    viaje.duracion_dias or "",
                    "Sí" if viaje.favorito else "No",
                    viaje.calificacion or "",
                    viaje.usuario.username,
                ]
            )
        return respuesta


# ---------------------------------------------------------------------------
# País
# ---------------------------------------------------------------------------
@admin.register(Pais)
class PaisAdmin(admin.ModelAdmin):
    list_display = ("nombre_con_bandera", "codigo_iso", "continente", "cantidad_viajes")
    list_filter = ("continente",)
    search_fields = ("nombre", "codigo_iso")
    ordering = ("nombre",)
    list_per_page = 50
    show_facets = admin.ShowFacets.ALWAYS

    def get_queryset(self, request):
        filtro = None if request.user.is_superuser else Q(viajes__usuario=request.user)
        return super().get_queryset(request).annotate(total_viajes=Count("viajes", filter=filtro))

    @admin.display(description="país", ordering="nombre")
    def nombre_con_bandera(self, obj):
        return f"{obj.bandera} {obj.nombre}"

    @admin.display(description="viajes", ordering="total_viajes")
    def cantidad_viajes(self, obj):
        return obj.total_viajes
