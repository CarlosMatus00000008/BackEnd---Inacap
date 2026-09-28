from django.conf import settings
from django.db import models


class PerfilUsuario(models.Model):
    """
    Datos extra de cada cuenta. El proyecto usa el User estándar de Django,
    así que el consentimiento (Ley N° 19.628 y N° 21.719) se guarda aquí.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil", verbose_name="usuario"
    )
    acepta_datos = models.BooleanField("acepta tratamiento de datos", default=False)
    fecha_consentimiento = models.DateTimeField("fecha del consentimiento", null=True, blank=True)

    class Meta:
        verbose_name = "perfil de usuario"
        verbose_name_plural = "perfiles de usuario"

    def __str__(self):
        return f"Perfil de {self.usuario}"
