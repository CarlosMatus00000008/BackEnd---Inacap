from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class PerfilUsuario(models.Model):
    """
    Perfil extendido de cada usuario del sistema.

    Aquí vive el control de permisos: el superusuario decide, para cada
    usuario nuevo, si puede subir/editar sus propios viajes y si puede ver
    el diario de viajes de los demás usuarios (modo "solo lectura").

    Se crea automáticamente al registrarse un usuario nuevo (ver signals.py),
    siempre con los dos permisos en False: un usuario recién registrado no
    puede hacer nada hasta que el superusuario se lo habilite.
    """

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="perfil",
    )
    puede_crear_viajes = models.BooleanField(
        default=False,
        verbose_name="Puede crear y editar viajes",
        help_text="Si está activo, el usuario puede subir nuevos viajes y editar los suyos.",
    )
    puede_ver_otros = models.BooleanField(
        default=False,
        verbose_name="Puede ver viajes de otros usuarios",
        help_text="Si está activo, el usuario puede ver el diario de viajes de todos (solo lectura).",
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"Perfil de {self.usuario.username}"


class Viaje(models.Model):
    """
    Un viaje del diario personal de un usuario.

    El estado (completado / en_progreso / planificado) NO se elige a mano:
    se recalcula solo, en cada guardado, a partir de fecha_inicio y
    fecha_fin comparadas con la fecha de hoy (ver calcular_estado()).
    """

    COMPLETADO = "completado"
    EN_PROGRESO = "en_progreso"
    PLANIFICADO = "planificado"
    ESTADO_CHOICES = [
        (COMPLETADO, "Completado"),
        (EN_PROGRESO, "En progreso"),
        (PLANIFICADO, "Planificado"),
    ]

    propietario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="viajes",
        verbose_name="Propietario",
    )
    destino = models.CharField(
        max_length=100,
        verbose_name="Destino",
        help_text='Ciudad o región, ej: "París", "Bali", "Cartagena".',
    )
    pais = models.CharField(max_length=100, verbose_name="País")
    fecha_inicio = models.DateField(verbose_name="Fecha de inicio")
    fecha_fin = models.DateField(
        verbose_name="Fecha de término",
        null=True,
        blank=True,
        help_text="Déjalo vacío si el viaje todavía no termina o es un plan a futuro.",
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default=PLANIFICADO,
        editable=False,
        verbose_name="Estado",
    )
    notas = models.TextField(
        blank=True,
        verbose_name="Notas del viaje",
        help_text="Detalles, recuerdos o lo que quieras anotar sobre este viaje.",
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_inicio"]  # más reciente primero
        verbose_name = "Viaje"
        verbose_name_plural = "Viajes"

    def __str__(self):
        return f"{self.destino}, {self.pais} ({self.get_estado_display()})"

    def calcular_estado(self):
        """Determina el estado del viaje solo a partir de las fechas."""
        hoy = timezone.localdate()
        if self.fecha_inicio > hoy:
            return self.PLANIFICADO
        if self.fecha_fin and self.fecha_fin < hoy:
            return self.COMPLETADO
        return self.EN_PROGRESO

    def save(self, *args, **kwargs):
        self.estado = self.calcular_estado()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("detalle_viaje", kwargs={"pk": self.pk})

    @property
    def duracion_dias(self):
        fin = self.fecha_fin or timezone.localdate()
        dias = (fin - self.fecha_inicio).days + 1
        return max(dias, 1)

    @property
    def total_mg(self):
        return self.mg.count()

    def con_mg_de(self, usuario):
        """¿Este usuario ya le dio 'mg' a este viaje?"""
        if not usuario or not usuario.is_authenticated:
            return False
        return self.mg.filter(usuario=usuario).exists()

    @property
    def fotos_restantes(self):
        return max(FotoViaje.MAX_FOTOS_POR_VIAJE - self.fotos.count(), 0)


class FotoViaje(models.Model):
    """
    Fotos del viaje. Máximo 2 por viaje (MAX_FOTOS_POR_VIAJE) — la vista
    valida ese límite antes de guardar una nueva. Cualquiera que pueda ver
    el viaje (propietario, o un usuario con puede_ver_otros) ve sus fotos,
    porque se muestran dentro de las mismas páginas que ya están protegidas
    por permisos (detalle del viaje y feed).
    """

    MAX_FOTOS_POR_VIAJE = 2

    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name="fotos")
    imagen = models.ImageField(upload_to="viajes/%Y/%m/", verbose_name="Foto")
    subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["subida"]
        verbose_name = "Foto de viaje"
        verbose_name_plural = "Fotos de viaje"

    def __str__(self):
        return f"Foto de {self.viaje}"


class Mg(models.Model):
    """
    El 'me gusta' del diario de viajes (como Instagram, pero SOLO mg,
    sin comentarios). Un usuario puede darle mg a un viaje una sola vez.
    """

    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name="mg")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mg_dados"
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("viaje", "usuario")
        verbose_name = "Mg"
        verbose_name_plural = "Mg"
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.usuario.username} → {self.viaje}"
