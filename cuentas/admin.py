from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.db.models import Count

from .models import PerfilUsuario

Usuario = get_user_model()

admin.site.unregister(Usuario)


class PerfilUsuarioInline(admin.StackedInline):
    """Teléfono y consentimiento de datos personales (el consentimiento es solo lectura: es la constancia)."""

    model = PerfilUsuario
    can_delete = False
    fields = ("telefono", "acepta_datos", "fecha_consentimiento")
    readonly_fields = ("acepta_datos", "fecha_consentimiento")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Admin de usuarios con columnas extra: grupos y cantidad de viajes."""

    inlines = (PerfilUsuarioInline,)

    list_display = (
        "username",
        "email",
        "first_name",
        "lista_grupos",
        "cantidad_viajes",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "groups", ("date_joined", admin.DateFieldListFilter))
    ordering = ("-date_joined",)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(total_viajes=Count("viajes", distinct=True))
            .prefetch_related("groups")
        )

    @admin.display(description="grupos")
    def lista_grupos(self, obj):
        return ", ".join(grupo.name for grupo in obj.groups.all()) or "—"

    @admin.display(description="viajes", ordering="total_viajes")
    def cantidad_viajes(self, obj):
        return obj.total_viajes
