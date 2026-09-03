from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PerfilUsuario


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_o_actualizar_perfil(sender, instance, created, **kwargs):
    """
    Cada vez que se crea un usuario (registro normal o `createsuperuser`),
    le creamos su PerfilUsuario automáticamente.

    - Usuario normal nuevo -> perfil con los dos permisos en False.
      El superusuario debe habilitarlos desde /usuarios/.
    - Superusuario (is_superuser=True) -> perfil con todos los permisos
      activados de entrada, porque un superusuario ya puede manejar todo.
    """
    if created:
        PerfilUsuario.objects.get_or_create(
            usuario=instance,
            defaults={
                "puede_crear_viajes": instance.is_superuser,
                "puede_ver_otros": instance.is_superuser,
            },
        )
    elif instance.is_superuser:
        # Si a un usuario existente lo vuelven superusuario, aseguramos
        # que tenga siempre ambos permisos.
        PerfilUsuario.objects.update_or_create(
            usuario=instance,
            defaults={"puede_crear_viajes": True, "puede_ver_otros": True},
        )
