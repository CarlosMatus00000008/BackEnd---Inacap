"""
Formularios del diario. Cada uno valida:
  1) el tipo de dato (texto, fecha, opción…),
  2) el contenido (reglas del negocio en los modelos: fechas coherentes y estados),
  3) y sanitiza el texto (TextoField / TextoLargoField quitan HTML y caracteres invisibles).
"""

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.urls import reverse_lazy

from core.formularios import FechaInput, FormularioBase, TextoField, TextoLargoField

from .models import EstadoViaje, Pais, Viaje

Usuario = get_user_model()
MAXIMO_COMPARTIDOS = 10


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
        ]
        field_classes = {"destino": TextoField, "notas": TextoLargoField}
        widgets = {
            "destino": forms.TextInput(attrs={"placeholder": "Ej: París", "autocomplete": "off"}),
            "fecha_inicio": FechaInput(),
            "fecha_fin": FechaInput(),
            "estado": forms.RadioSelect,
            "notas": forms.Textarea(
                attrs={"rows": 5, "placeholder": "¿Qué pasó en este viaje? ¿Qué no te puedes olvidar?"}
            ),
        }
        labels = {"favorito": "Marcar como favorito ★"}

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.fields["pais"].queryset = Pais.objects.order_by("nombre")
        self.fields["pais"].empty_label = "Elige un país…"
        self.fields["calificacion"].choices = [("", "Sin calificar"), *self.fields["calificacion"].choices[1:]]
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
