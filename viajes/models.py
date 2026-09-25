"""
Modelos (tablas) del Diario de Viajes.

    Pais ──< Viaje >── Usuario (dueño)
                  └──<< compartido_con (usuarios que pueden verlo, solo lectura)

«──<» = relación uno a muchos (ForeignKey) · «>>──<<» = muchos a muchos.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone

from .validadores import validar_texto_con_letras


# ---------------------------------------------------------------------------
# Opciones (choices)
# ---------------------------------------------------------------------------
class Continente(models.TextChoices):
    AFRICA = "africa", "África"
    AMERICA_NORTE = "america_norte", "América del Norte"
    AMERICA_CENTRAL = "america_central", "Centroamérica y el Caribe"
    AMERICA_SUR = "america_sur", "América del Sur"
    ASIA = "asia", "Asia"
    EUROPA = "europa", "Europa"
    OCEANIA = "oceania", "Oceanía"


class EstadoViaje(models.TextChoices):
    COMPLETADO = "completado", "Completado"
    EN_PROGRESO = "en_progreso", "En progreso"
    PLANIFICADO = "planificado", "Planificado"


CALIFICACIONES = [
    (5, "★★★★★ Inolvidable"),
    (4, "★★★★☆ Muy bueno"),
    (3, "★★★☆☆ Bueno"),
    (2, "★★☆☆☆ Regular"),
    (1, "★☆☆☆☆ Malo"),
]


# ---------------------------------------------------------------------------
# País
# ---------------------------------------------------------------------------
class Pais(models.Model):
    """Catálogo de países (se carga automáticamente con las migraciones)."""

    nombre = models.CharField("nombre", max_length=80, unique=True)
    codigo_iso = models.CharField(
        "código ISO",
        max_length=2,
        unique=True,
        validators=[RegexValidator(r"^[A-Z]{2}$", "Usa 2 letras mayúsculas, por ejemplo: CL.")],
        help_text="Código ISO 3166-1 de 2 letras, por ejemplo: CL, FR, JP.",
    )
    continente = models.CharField("continente", max_length=20, choices=Continente.choices, db_index=True)

    class Meta:
        verbose_name = "país"
        verbose_name_plural = "países"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def bandera(self) -> str:
        """Emoji de la bandera a partir del código ISO (CL → 🇨🇱)."""
        return "".join(chr(0x1F1E6 + ord(letra) - ord("A")) for letra in self.codigo_iso.upper())


# ---------------------------------------------------------------------------
# Viaje
# ---------------------------------------------------------------------------
class ViajeQuerySet(models.QuerySet):
    """Consultas reutilizables: los permisos se aplican SIEMPRE desde aquí."""

    def de_usuario(self, usuario):
        """Solo los viajes cuyo dueño es el usuario."""
        return self.filter(usuario=usuario)

    def compartidos_con(self, usuario):
        """Viajes de otras personas que compartieron conmigo (solo lectura)."""
        return self.filter(compartido_con=usuario).exclude(usuario=usuario)

    def visibles_para(self, usuario):
        """Viajes propios + viajes compartidos conmigo."""
        compartidos = Viaje.objects.filter(compartido_con=usuario).values("pk")
        return self.filter(Q(usuario=usuario) | Q(pk__in=compartidos))

    def completados(self):
        return self.filter(estado=EstadoViaje.COMPLETADO)

    def en_progreso(self):
        return self.filter(estado=EstadoViaje.EN_PROGRESO)

    def planificados(self):
        return self.filter(estado=EstadoViaje.PLANIFICADO)

    def con_resumen(self):
        """País y dueño en la misma consulta (para listados sin consultas repetidas)."""
        return self.select_related("pais", "usuario")


class Viaje(models.Model):
    """Un viaje realizado, en curso o planificado por un usuario."""

    Estado = EstadoViaje
    ICONOS_ESTADO = {
        EstadoViaje.COMPLETADO: "✓",
        EstadoViaje.EN_PROGRESO: "🔄",
        EstadoViaje.PLANIFICADO: "📋",
    }

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="viajes",
        verbose_name="viajero",
    )
    destino = models.CharField(
        "destino",
        max_length=100,
        validators=[validar_texto_con_letras],
        help_text="Ciudad o región, por ejemplo: París, Bali, Cartagena.",
    )
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, related_name="viajes", verbose_name="país")
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_fin = models.DateField(
        "fecha de regreso",
        null=True,
        blank=True,
        help_text="Opcional si el viaje aún no termina o todavía no la conoces.",
    )
    estado = models.CharField("estado", max_length=12, choices=EstadoViaje.choices, default=EstadoViaje.PLANIFICADO)
    notas = models.TextField("notas", blank=True, max_length=5000, help_text="Lo que pasó, recuerdos, recomendaciones…")
    favorito = models.BooleanField("favorito", default=False)
    calificacion = models.PositiveSmallIntegerField(
        "calificación",
        null=True,
        blank=True,
        choices=CALIFICACIONES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    compartido_con = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="viajes_compartidos",
        verbose_name="compartido con",
        help_text="Personas que pueden ver este viaje (solo lectura).",
    )
    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    objects = ViajeQuerySet.as_manager()

    class Meta:
        verbose_name = "viaje"
        verbose_name_plural = "viajes"
        ordering = ["-fecha_inicio", "-creado"]  # del más reciente al más antiguo
        indexes = [
            models.Index(fields=["usuario", "-fecha_inicio"], name="viaje_usuario_fecha_idx"),
            models.Index(fields=["usuario", "estado"], name="viaje_usuario_estado_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=F("fecha_inicio")),
                name="viaje_regreso_posterior_inicio",
                violation_error_message="La fecha de regreso no puede ser anterior a la de inicio.",
            ),
            models.CheckConstraint(
                condition=Q(calificacion__isnull=True) | Q(calificacion__gte=1, calificacion__lte=5),
                name="viaje_calificacion_1_a_5",
            ),
            models.UniqueConstraint(
                fields=["usuario"],
                condition=Q(estado="en_progreso"),
                name="viaje_un_solo_viaje_en_progreso",
                violation_error_message="Solo puedes tener un viaje en progreso a la vez.",
            ),
        ]

    def __str__(self):
        return f"{self.destino}, {self.pais} ({self.fecha_inicio:%Y})"

    def get_absolute_url(self):
        return reverse("viajes:detalle", kwargs={"pk": self.pk})

    # --- Validación de reglas del negocio -------------------------------------
    def clean(self):
        super().clean()
        errores = {}
        hoy = timezone.localdate()
        inicio, fin = self.fecha_inicio, self.fecha_fin

        if inicio and fin and fin < inicio:
            errores["fecha_fin"] = "La fecha de regreso no puede ser anterior a la fecha de inicio."

        if inicio and "fecha_fin" not in errores:
            if self.estado == EstadoViaje.COMPLETADO:
                if inicio > hoy:
                    errores["estado"] = (
                        "Un viaje completado no puede comenzar en el futuro: márcalo como «Planificado»."
                    )
                elif not fin:
                    errores["fecha_fin"] = "Indica la fecha de regreso de un viaje completado."
                elif fin > hoy:
                    errores["fecha_fin"] = "Un viaje completado no puede terminar después de hoy."
            elif self.estado == EstadoViaje.EN_PROGRESO:
                if inicio > hoy:
                    errores["estado"] = "Este viaje aún no comienza: márcalo como «Planificado»."
                elif fin and fin < hoy:
                    errores["estado"] = "La fecha de regreso ya pasó: márcalo como «Completado»."
            elif self.estado == EstadoViaje.PLANIFICADO and inicio < hoy:
                errores["estado"] = (
                    "Un viaje planificado debe comenzar hoy o más adelante. "
                    "Si ya comenzó, márcalo como «En progreso» o «Completado»."
                )

        if self.calificacion and self.estado == EstadoViaje.PLANIFICADO:
            errores["calificacion"] = "Solo puedes calificar viajes que ya comenzaste o completaste."

        if self.estado == EstadoViaje.EN_PROGRESO and self.usuario_id and "estado" not in errores:
            otro = (
                Viaje.objects.filter(usuario_id=self.usuario_id, estado=EstadoViaje.EN_PROGRESO)
                .exclude(pk=self.pk)
                .select_related("pais")
                .first()
            )
            if otro:
                errores["estado"] = f"Ya tienes un viaje en progreso ({otro}). Márcalo como completado primero."

        if errores:
            raise ValidationError(errores)

    # --- Datos calculados ------------------------------------------------------
    @property
    def icono_estado(self) -> str:
        return self.ICONOS_ESTADO.get(self.estado, "")

    @property
    def duracion_dias(self) -> int | None:
        """Duración aproximada en días (incluye el día de salida y el de regreso)."""
        if self.fecha_inicio and self.fecha_fin:
            return (self.fecha_fin - self.fecha_inicio).days + 1
        if self.fecha_inicio and self.estado == EstadoViaje.EN_PROGRESO:
            return max((timezone.localdate() - self.fecha_inicio).days + 1, 1)
        return None

    @property
    def estado_sugerido(self) -> str:
        """Estado que corresponde según las fechas y el día de hoy."""
        hoy = timezone.localdate()
        if self.fecha_inicio > hoy:
            return EstadoViaje.PLANIFICADO
        if self.fecha_fin and self.fecha_fin < hoy:
            return EstadoViaje.COMPLETADO
        return EstadoViaje.EN_PROGRESO

    @property
    def estado_sugerido_display(self) -> str:
        return EstadoViaje(self.estado_sugerido).label

    @property
    def estado_desactualizado(self) -> bool:
        """True si el paso del tiempo dejó el estado desfasado (ej.: el viaje ya empezó)."""
        return self.estado != EstadoViaje.COMPLETADO and self.estado != self.estado_sugerido

    @property
    def dias_para_comenzar(self) -> int | None:
        if self.estado != EstadoViaje.PLANIFICADO:
            return None
        return (self.fecha_inicio - timezone.localdate()).days

    def aplicar_estado(self, nuevo_estado: str) -> list[str]:
        """
        Cambia el estado y ajusta la fecha de regreso cuando corresponde.
        Devuelve la lista de ajustes realizados (para informar al usuario).
        La validación final la hace full_clean() en la vista.
        """
        ajustes = []
        hoy = timezone.localdate()
        self.estado = nuevo_estado
        regreso_pendiente = self.fecha_fin is None or self.fecha_fin > hoy
        if nuevo_estado == EstadoViaje.COMPLETADO and self.fecha_inicio <= hoy and regreso_pendiente:
            self.fecha_fin = hoy
            ajustes.append(f"la fecha de regreso quedó en hoy ({hoy:%d-%m-%Y})")
        return ajustes

    def es_de(self, usuario) -> bool:
        return usuario.is_authenticated and self.usuario_id == usuario.pk
