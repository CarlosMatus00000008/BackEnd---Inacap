"""
Modelos (tablas) del Diario de Viajes.

    Pais ──< Viaje >── Usuario (dueño)
                  ├──<< compartido_con (usuarios que pueden verlo, solo lectura)
                  ├──< Actividad   (itinerario día a día)
                  ├──< Gasto       (gastos del viaje, comparados con Viaje.presupuesto)
                  ├──< FotoViaje   (fotos guardadas en Supabase Storage)
                  └──< EnlaceFotos (enlaces privados para ver solo las fotos, enviados por WhatsApp)

«──<» = relación uno a muchos (ForeignKey) · «>>──<<» = muchos a muchos.
"""

import secrets
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone

from . import monedas
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
    presupuesto = models.PositiveIntegerField(
        "presupuesto",
        null=True,
        blank=True,
        validators=[MaxValueValidator(999_999_999)],
        help_text="Opcional. En pesos chilenos, sin puntos: por ejemplo 850000.",
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


# ---------------------------------------------------------------------------
# Itinerario del viaje
# ---------------------------------------------------------------------------
class Actividad(models.Model):
    """Una actividad del itinerario día a día. Solo el dueño del viaje puede agregarla, marcarla o eliminarla."""

    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name="actividades", verbose_name="viaje")
    fecha = models.DateField("día")
    hora = models.TimeField("hora", null=True, blank=True, help_text="Opcional.")
    titulo = models.CharField(
        "actividad",
        max_length=120,
        validators=[validar_texto_con_letras],
        help_text="Ej: Tour por el centro histórico.",
    )
    lugar = models.CharField("lugar", max_length=120, blank=True, help_text="Opcional. Ej: Plaza de Armas.")
    realizada = models.BooleanField("realizada", default=False)
    creado = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "actividad"
        verbose_name_plural = "actividades"
        # Por día y por hora; las que no tienen hora van al final de su día.
        ordering = ["fecha", F("hora").asc(nulls_last=True), "creado"]
        indexes = [models.Index(fields=["viaje", "fecha"], name="actividad_viaje_fecha_idx")]

    def __str__(self):
        return f"{self.titulo} ({self.fecha:%d-%m-%Y})"

    def clean(self):
        super().clean()
        if not (self.fecha and self.viaje_id):
            return
        inicio, fin = self.viaje.fecha_inicio, self.viaje.fecha_fin
        if self.fecha < inicio:
            raise ValidationError({"fecha": f"El viaje comienza el {inicio:%d-%m-%Y}: elige un día desde esa fecha."})
        if fin and self.fecha > fin:
            raise ValidationError({"fecha": f"El viaje termina el {fin:%d-%m-%Y}: elige un día hasta esa fecha."})

    @property
    def numero_dia(self) -> int:
        """1 para el primer día del viaje, 2 para el segundo, etc."""
        return (self.fecha - self.viaje.fecha_inicio).days + 1


# ---------------------------------------------------------------------------
# Gastos del viaje
# ---------------------------------------------------------------------------
class CategoriaGasto(models.TextChoices):
    TRANSPORTE = "transporte", "🚌 Transporte"
    ALOJAMIENTO = "alojamiento", "🏨 Alojamiento"
    COMIDA = "comida", "🍽️ Comida"
    ACTIVIDADES = "actividades", "🎟️ Actividades"
    COMPRAS = "compras", "🛍️ Compras"
    OTROS = "otros", "📦 Otros"


class Gasto(models.Model):
    """
    Un gasto del viaje, en pesos chilenos. Solo el dueño del viaje puede agregarlos o eliminarlos.
    Si se pagó en otra moneda, se guarda también ese monto (moneda + monto_moneda) como registro.
    """

    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name="gastos", verbose_name="viaje")
    descripcion = models.CharField(
        "descripción", max_length=120, validators=[validar_texto_con_letras], help_text="Ej: Vuelo Santiago–Lima."
    )
    categoria = models.CharField(
        "categoría", max_length=12, choices=CategoriaGasto.choices, default=CategoriaGasto.OTROS
    )
    monto = models.PositiveIntegerField(
        "monto", validators=[MinValueValidator(1), MaxValueValidator(999_999_999)], help_text="En pesos chilenos."
    )
    moneda = models.CharField(
        "moneda", max_length=3, blank=True, choices=monedas.OPCIONES, help_text="Opcional. La moneda en que pagaste."
    )
    monto_moneda = models.DecimalField(
        "monto en esa moneda",
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("9999999999999"))],
    )
    fecha = models.DateField("fecha", default=timezone.localdate)
    creado = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "gasto"
        verbose_name_plural = "gastos"
        ordering = ["-fecha", "-creado"]
        constraints = [
            models.CheckConstraint(condition=Q(monto__gt=0), name="gasto_monto_positivo"),
            # La moneda y su monto van juntos: los dos o ninguno.
            models.CheckConstraint(
                condition=Q(moneda="", monto_moneda__isnull=True) | (~Q(moneda="") & Q(monto_moneda__isnull=False)),
                name="gasto_moneda_completa",
            ),
        ]

    def __str__(self):
        return f"{self.descripcion} (${self.monto})"

    def clean(self):
        super().clean()
        if self.monto_moneda is not None and not self.moneda:
            raise ValidationError({"moneda": "Elige en qué moneda pagaste."})
        if self.moneda and self.monto_moneda is None:
            raise ValidationError({"monto_moneda": f"Escribe cuánto pagaste en {monedas.nombre_moneda(self.moneda)}."})


# ---------------------------------------------------------------------------
# Fotos del viaje
# ---------------------------------------------------------------------------
def ruta_foto(foto, nombre_original: str) -> str:
    """viajes/<usuario>/<viaje>/<aleatorio>.jpg → nombres imposibles de adivinar y sin datos personales."""
    extension = Path(nombre_original).suffix.lower() or ".jpg"
    return f"viajes/{foto.viaje.usuario_id}/{foto.viaje_id}/{uuid.uuid4().hex}{extension}"


class FotoViaje(models.Model):
    """Foto de un viaje. La ven el dueño y las personas con quienes se compartió el viaje."""

    MAXIMO_POR_VIAJE = 10

    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name="fotos", verbose_name="viaje")
    imagen = models.ImageField("foto", upload_to=ruta_foto, max_length=200)
    credito = models.CharField(
        "crédito", max_length=200, blank=True, help_text="Autor y licencia, si la foto no es propia."
    )
    subida = models.DateTimeField("subida", auto_now_add=True)

    class Meta:
        verbose_name = "foto de viaje"
        verbose_name_plural = "fotos de viaje"
        ordering = ["subida"]

    def __str__(self):
        return f"Foto de {self.viaje}"


# ---------------------------------------------------------------------------
# Enlaces privados a las fotos de un viaje
# ---------------------------------------------------------------------------
def generar_token() -> str:
    """43 caracteres aleatorios (256 bits): imposible de adivinar."""
    return secrets.token_urlsafe(32)


class EnlaceFotosQuerySet(models.QuerySet):
    def vigentes(self):
        return self.filter(vence__gt=timezone.now())


class EnlaceFotos(models.Model):
    """
    Enlace privado para ver SOLO las fotos de un viaje, sin cuenta: el dueño lo envía por WhatsApp.
    Quien lo abre no ve notas, gastos ni nada más del viaje o del sitio. Deja de funcionar
    cuando vence o cuando el dueño lo revoca (se elimina).
    """

    VIGENCIAS = [(1, "24 horas"), (7, "7 días"), (30, "30 días")]

    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name="enlaces_fotos", verbose_name="viaje")
    token = models.CharField("código", max_length=64, unique=True, default=generar_token, editable=False)
    telefono = models.CharField("teléfono", max_length=20, help_text="A quién se le envió, en formato +56912345678.")
    creado = models.DateTimeField("creado", auto_now_add=True)
    vence = models.DateTimeField("vence")

    objects = EnlaceFotosQuerySet.as_manager()

    class Meta:
        verbose_name = "enlace a las fotos"
        verbose_name_plural = "enlaces a las fotos"
        ordering = ["-creado"]

    def __str__(self):
        return f"Fotos de {self.viaje} para {self.telefono}"

    def get_absolute_url(self):
        return reverse("viajes:fotos_publicas", args=[self.token])

    @classmethod
    def crear(cls, viaje, telefono: str, dias: int):
        return cls.objects.create(viaje=viaje, telefono=telefono, vence=timezone.now() + timedelta(days=dias))
