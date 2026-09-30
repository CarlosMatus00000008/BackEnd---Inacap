"""
Formularios del diario. Cada uno valida:
  1) el tipo de dato (texto, fecha, opción…),
  2) el contenido (reglas del negocio en los modelos: fechas coherentes y estados),
  3) y sanitiza el texto (TextoField / TextoLargoField quitan HTML y caracteres invisibles).
"""

import re
from io import BytesIO
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db.models import Q
from django.urls import reverse_lazy
from PIL import Image, ImageOps

from core.formularios import FechaInput, FormularioBase, TextoField, TextoLargoField
from cuentas.forms import TelefonoField

from .models import Actividad, EnlaceFotos, EstadoViaje, FotoViaje, Gasto, Pais, Viaje
from .monedas import MONEDA_DE_PAIS

Usuario = get_user_model()
MAXIMO_COMPARTIDOS = 10


class MontoField(forms.IntegerField):
    """
    Monto en pesos chilenos. Acepta cómo se escribe en Chile: «25.000», «$25.000» o «25000».
    (Un <input type="number"> leería «25.000» como 25; por eso es un campo de texto numérico.)
    static/js/montos.js le agrega los puntos de miles mientras se escribe.
    """

    widget = forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off", "data-monto": "entero"})

    def to_python(self, value):
        if isinstance(value, str):
            if "," in value:
                # «25.000,50» no puede convertirse en 2.500.050: los pesos chilenos no llevan decimales.
                raise forms.ValidationError("Los montos en pesos chilenos van sin decimales.", code="con_decimales")
            value = re.sub(r"[\s$.]", "", value)
        return super().to_python(value)


class CantidadField(forms.DecimalField):
    """
    Monto en moneda extranjera, con hasta 2 decimales. Acepta la escritura chilena
    («1.400.000», «12,50», «1.234,56») y también «12.50». Con coma, el punto es de miles;
    sin coma, el punto es de miles solo si separa grupos de 3 cifras («1.500» = mil quinientos).
    """

    widget = forms.TextInput(attrs={"inputmode": "decimal", "autocomplete": "off", "data-monto": "decimal"})

    def to_python(self, value):
        if isinstance(value, str):
            value = re.sub(r"[\s$€£¥]", "", value)
            if "," in value:
                value = value.replace(".", "").replace(",", ".")
            elif re.fullmatch(r"\d{1,3}(\.\d{3})+", value):
                value = value.replace(".", "")
        return super().to_python(value)


class ViajeForm(FormularioBase, forms.ModelForm):
    # Sin JavaScript es un texto con nombres separados por coma. Con JavaScript,
    # static/js/buscador-usuarios.js lo convierte en un buscador con sugerencias.
    compartir_con = TextoField(
        label="Compartir con",
        required=False,
        max_length=300,
        help_text="Nombres de usuario separados por coma (ej: pareja, camila_r). "
        "Podrán ver este viaje, pero no modificarlo.",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "data-buscar-usuarios": reverse_lazy("cuentas:buscar_usuarios"),
                "data-maximo": MAXIMO_COMPARTIDOS,
                "data-ayuda": "Escribe al menos 2 letras de su nombre y elige a la persona de la lista. "
                "Podrá ver este viaje, pero no modificarlo.",
            }
        ),
    )

    class Meta:
        model = Viaje
        fields = [
            "destino",
            "pais",
            "fecha_inicio",
            "fecha_fin",
            "estado",
            "notas",
            "favorito",
            "calificacion",
            "presupuesto",
        ]
        field_classes = {"destino": TextoField, "notas": TextoLargoField, "presupuesto": MontoField}
        widgets = {
            "destino": forms.TextInput(attrs={"placeholder": "Ej: París", "autocomplete": "off"}),
            "fecha_inicio": FechaInput(),
            "fecha_fin": FechaInput(),
            "estado": forms.RadioSelect,
            "notas": forms.Textarea(
                attrs={"rows": 5, "placeholder": "¿Qué pasó en este viaje? ¿Qué no te puedes olvidar?"}
            ),
        }
        labels = {"favorito": "Marcar como favorito ★", "presupuesto": "Presupuesto total (CLP)"}

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.fields["pais"].queryset = Pais.objects.order_by("nombre")
        self.fields["pais"].empty_label = "Elige un país…"
        self.fields["calificacion"].choices = [("", "Sin calificar"), *self.fields["calificacion"].choices[1:]]
        self.fields["presupuesto"].widget.attrs["placeholder"] = "Ej: 850.000"
        if self.instance.pk:
            nombres = self.instance.compartido_con.order_by("username").values_list("username", flat=True)
            self.initial["compartir_con"] = ", ".join(nombres)

    def clean_compartir_con(self):
        texto = self.cleaned_data.get("compartir_con") or ""
        nombres = list(dict.fromkeys(nombre.strip() for nombre in texto.split(",") if nombre.strip()))
        if len(nombres) > MAXIMO_COMPARTIDOS:
            raise forms.ValidationError(f"Puedes compartir un viaje con hasta {MAXIMO_COMPARTIDOS} personas.")

        usuarios, no_encontrados = [], []
        for nombre in nombres:
            usuario = Usuario.objects.filter(username__iexact=nombre, is_active=True).first()
            if usuario is None:
                no_encontrados.append(nombre)
            elif usuario.pk == self.usuario.pk:
                raise forms.ValidationError("No necesitas compartir el viaje contigo mismo.")
            else:
                usuarios.append(usuario)
        if no_encontrados:
            raise forms.ValidationError(f"No encontramos estos usuarios: {', '.join(no_encontrados)}.")
        return usuarios

    def _save_m2m(self):
        super()._save_m2m()
        self.instance.compartido_con.set(self.cleaned_data.get("compartir_con", []))


class FiltroViajesForm(FormularioBase, forms.Form):
    """Filtros de la línea de tiempo (llegan por GET y también se validan)."""

    ESTADOS = [
        ("", "Todos"),
        ("completados", "✓ Completados"),
        ("en-progreso", "🔄 En progreso"),
        ("pendientes", "📋 Pendientes"),
    ]
    ESTADO_POR_FILTRO = {
        "completados": EstadoViaje.COMPLETADO,
        "en-progreso": EstadoViaje.EN_PROGRESO,
        "pendientes": EstadoViaje.PLANIFICADO,
    }

    q = TextoField(label="Buscar", required=False, max_length=80)
    estado = forms.ChoiceField(label="Estado", choices=ESTADOS, required=False)
    anio = forms.TypedChoiceField(label="Año", coerce=int, required=False, empty_value=None)
    favoritos = forms.BooleanField(label="Solo favoritos", required=False)

    def __init__(self, *args, anios=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["q"].widget.attrs.update(placeholder="Destino, país o notas…", type="search")
        self.fields["anio"].choices = [("", "Todos los años"), *[(anio, anio) for anio in anios]]

    def filtrar(self, consulta):
        if not self.is_valid():
            return consulta
        datos = self.cleaned_data
        if datos["q"]:
            consulta = consulta.filter(
                Q(destino__icontains=datos["q"])
                | Q(pais__nombre__icontains=datos["q"])
                | Q(notas__icontains=datos["q"])
            )
        if datos["estado"]:
            consulta = consulta.filter(estado=self.ESTADO_POR_FILTRO[datos["estado"]])
        if datos["anio"]:
            consulta = consulta.filter(fecha_inicio__year=datos["anio"])
        if datos["favoritos"]:
            consulta = consulta.filter(favorito=True)
        return consulta

    @property
    def activos(self) -> bool:
        return self.is_valid() and any(self.cleaned_data.values())


class CambiarEstadoForm(forms.Form):
    estado = forms.ChoiceField(choices=EstadoViaje.choices)


# ---------------------------------------------------------------------------
# Gastos
# ---------------------------------------------------------------------------
class GastoForm(FormularioBase, forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ["descripcion", "categoria", "monto", "fecha", "moneda", "monto_moneda"]
        field_classes = {"descripcion": TextoField, "monto": MontoField, "monto_moneda": CantidadField}
        widgets = {
            "descripcion": forms.TextInput(attrs={"placeholder": "Ej: Vuelo Santiago–Lima", "autocomplete": "off"}),
            "fecha": FechaInput(),
        }
        labels = {"monto": "Monto (CLP)"}
        help_texts = {
            "monto": "Lo que te costó en pesos chilenos.",
            "moneda": "",
            "monto_moneda": "Opcional. Déjalo vacío si pagaste en pesos chilenos.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["monto"].widget.attrs["placeholder"] = "Ej: 25.000"
        self.fields["monto_moneda"].widget.attrs["placeholder"] = "Ej: 110.000"
        self.fields["moneda"].choices = [("", "Solo pesos chilenos"), *self.fields["moneda"].choices[1:]]
        # Propone la moneda del país del viaje (Colombia → pesos colombianos)
        if not self.is_bound and not self.instance.moneda and self.instance.viaje_id:
            self.initial["moneda"] = MONEDA_DE_PAIS.get(self.instance.viaje.pais.codigo_iso, "")

    def clean(self):
        datos = super().clean()
        # La moneda viene propuesta: si no se escribió un monto en ella, el gasto fue solo en pesos.
        if datos.get("monto_moneda") is None and "monto_moneda" not in self.errors:
            datos["moneda"] = ""
        return datos


# ---------------------------------------------------------------------------
# Itinerario
# ---------------------------------------------------------------------------
class ActividadForm(FormularioBase, forms.ModelForm):
    class Meta:
        model = Actividad
        fields = ["titulo", "fecha", "hora", "lugar"]
        field_classes = {"titulo": TextoField, "lugar": TextoField}
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Ej: Tour por el centro histórico", "autocomplete": "off"}),
            "fecha": FechaInput(),
            "hora": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "lugar": forms.TextInput(attrs={"placeholder": "Ej: Plaza de Armas", "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El calendario del navegador solo deja elegir días dentro del viaje.
        viaje = self.instance.viaje
        self.fields["fecha"].widget.attrs["min"] = viaje.fecha_inicio.isoformat()
        if viaje.fecha_fin:
            self.fields["fecha"].widget.attrs["max"] = viaje.fecha_fin.isoformat()


# ---------------------------------------------------------------------------
# Fotos
# ---------------------------------------------------------------------------
# «MPO» también es JPG: así guardan sus fotos el iPhone y muchas cámaras (un JPEG con una
# segunda imagen adentro). Al guardarla se conserva solo la foto principal.
FORMATOS_FOTO = {"JPEG", "MPO", "PNG", "WEBP"}
LADO_MAXIMO_FOTO = 2048  # píxeles: suficiente para verlas en pantalla y ahorra espacio en Supabase


class VariosArchivosInput(forms.FileInput):
    allow_multiple_selected = True


class VariasFotosField(forms.ImageField):
    """
    Varias fotos en un solo envío. Cada una se valida (tamaño, formato real con Pillow) y
    se vuelve a guardar: se endereza, se achica si es enorme y pierde los metadatos EXIF
    (que pueden incluir la ubicación GPS de quien tomó la foto).
    """

    widget = VariosArchivosInput(attrs={"accept": "image/jpeg,image/png,image/webp"})

    def clean(self, data, initial=None):
        archivos = data if isinstance(data, (list, tuple)) and data else [data]
        preparadas = []
        for archivo in archivos:
            preparadas.append(self._preparar(super().clean(archivo, initial)))
        return preparadas

    def _preparar(self, archivo):
        nombre = Path(archivo.name).name
        if archivo.size > settings.FOTO_TAMANO_MAXIMO_MB * 1024 * 1024:
            raise forms.ValidationError(
                f"«{nombre}» pesa más de {settings.FOTO_TAMANO_MAXIMO_MB} MB.", code="foto_pesada"
            )
        if archivo.image.format not in FORMATOS_FOTO:
            raise forms.ValidationError(f"«{nombre}» no es JPG, PNG ni WEBP.", code="foto_formato")
        try:
            archivo.seek(0)
            with Image.open(archivo) as original:
                imagen = ImageOps.exif_transpose(original)
                imagen.thumbnail((LADO_MAXIMO_FOTO, LADO_MAXIMO_FOTO))
                salida = BytesIO()
                if imagen.mode in ("RGBA", "LA") or (imagen.mode == "P" and "transparency" in imagen.info):
                    imagen.save(salida, "PNG", optimize=True)
                    extension = "png"
                else:
                    imagen.convert("RGB").save(salida, "JPEG", quality=85, optimize=True)
                    extension = "jpg"
        except (OSError, ValueError, Image.DecompressionBombError) as error:
            mensaje = f"No pudimos leer «{nombre}». Prueba con otra foto."
            raise forms.ValidationError(mensaje, code="foto_danada") from error
        return ContentFile(salida.getvalue(), name=f"foto.{extension}")


class FotosForm(FormularioBase, forms.Form):
    fotos = VariasFotosField(
        label="Fotos",
        help_text=f"JPG, PNG o WEBP · hasta {settings.FOTO_TAMANO_MAXIMO_MB} MB cada una. "
        "Puedes elegir varias a la vez.",
        error_messages={"required": "Elige al menos una foto."},
    )

    def __init__(self, *args, viaje, **kwargs):
        super().__init__(*args, **kwargs)
        self.disponibles = max(FotoViaje.MAXIMO_POR_VIAJE - viaje.fotos.count(), 0)

    def clean_fotos(self):
        fotos = self.cleaned_data["fotos"]
        if len(fotos) > self.disponibles:
            if self.disponibles == 0:
                mensaje = f"Este viaje ya tiene el máximo de {FotoViaje.MAXIMO_POR_VIAJE} fotos."
            else:
                mensaje = (
                    f"Elegiste {len(fotos)} fotos, pero solo puedes subir {self.disponibles} más "
                    f"(máximo {FotoViaje.MAXIMO_POR_VIAJE} por viaje)."
                )
            raise forms.ValidationError(mensaje, code="demasiadas_fotos")
        return fotos


# ---------------------------------------------------------------------------
# Compartir las fotos por WhatsApp
# ---------------------------------------------------------------------------
class CompartirFotosForm(FormularioBase, forms.Form):
    telefono = TelefonoField(
        label="Número de WhatsApp",
        max_length=20,
        help_text="Ejemplo: +56 9 1234 5678. Si no tiene prefijo, se asume Chile (+56).",
    )
    dias = forms.TypedChoiceField(
        label="El enlace funciona durante",
        choices=EnlaceFotos.VIGENCIAS,
        coerce=int,
        initial=7,
        widget=forms.RadioSelect,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["telefono"].widget.attrs.update(placeholder="+56 9 1234 5678", autocomplete="off")
