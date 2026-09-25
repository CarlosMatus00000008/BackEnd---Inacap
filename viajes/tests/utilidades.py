"""Funciones de apoyo para crear datos de prueba de forma breve y legible."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone

from viajes.models import EstadoViaje, Pais, Viaje
from viajes.senales import GRUPO_VIAJEROS

CONTRASENA = "Clave.Segura.2026"


def hoy():
    return timezone.localdate()


def crear_usuario(nombre="ana", viajero=True, **extra):
    usuario = get_user_model().objects.create_user(nombre, f"{nombre}@example.com", CONTRASENA, **extra)
    if viajero:
        usuario.groups.add(Group.objects.get(name=GRUPO_VIAJEROS))
    return usuario


def crear_viaje(usuario, **datos):
    """Por defecto: un viaje completado a Lima hace un mes."""
    valores = {
        "destino": "Lima",
        "pais": Pais.objects.get(codigo_iso="PE"),
        "fecha_inicio": hoy() - timedelta(days=30),
        "fecha_fin": hoy() - timedelta(days=25),
        "estado": EstadoViaje.COMPLETADO,
    }
    valores.update(datos)
    viaje = Viaje(usuario=usuario, **valores)
    viaje.full_clean()
    viaje.save()
    return viaje
