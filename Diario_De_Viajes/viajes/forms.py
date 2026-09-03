from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Viaje


class RegistroForm(UserCreationForm):
    """
    Formulario de registro público. Cualquiera puede crear una cuenta
    (usuario + contraseña), pero queda SIN permisos hasta que el
    superusuario se los otorgue desde el panel de Gestión de usuarios.
    """

    email = forms.EmailField(required=False, label="Correo (opcional)")

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs["class"] = "form-control"


class ViajeForm(forms.ModelForm):
    """
    Formulario de creación/edición de un viaje.
    El propietario y el estado NO se piden aquí: el propietario se asigna
    en la vista (request.user) y el estado se calcula solo a partir de
    las fechas (Viaje.calcular_estado).

    foto_1 / foto_2 no son campos del modelo Viaje (las fotos viven en
    FotoViaje, una tabla aparte) — la vista las toma de aquí y crea los
    objetos FotoViaje correspondientes, respetando el máximo de 2 por viaje.
    """

    foto_1 = forms.ImageField(required=False, label="Foto 1", widget=forms.ClearableFileInput(attrs={"class": "form-control"}))
    foto_2 = forms.ImageField(required=False, label="Foto 2", widget=forms.ClearableFileInput(attrs={"class": "form-control"}))

    class Meta:
        model = Viaje
        fields = ["destino", "pais", "fecha_inicio", "fecha_fin", "notas"]
        widgets = {
            "destino": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: París"}),
            "pais": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej: Francia"}),
            # format="%Y-%m-%d" es obligatorio: un <input type="date"> del navegador
            # SIEMPRE espera/entrega el valor en formato ISO (YYYY-MM-DD), sin
            # importar el idioma de la página. Como el proyecto usa LANGUAGE_CODE
            # "es-cl", sin este format Django precargaría la fecha en formato
            # chileno (dd/mm/yyyy) y el navegador no la reconocería al editar.
            "fecha_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "fecha_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "notas": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "placeholder": "¿Qué pasó en este viaje?"}
            ),
        }

    def clean(self):
        datos = super().clean()
        inicio = datos.get("fecha_inicio")
        fin = datos.get("fecha_fin")
        if inicio and fin and fin < inicio:
            self.add_error("fecha_fin", "La fecha de término no puede ser anterior a la de inicio.")
        return datos

    def fotos_nuevas(self):
        """Las fotos que sí se subieron en este envío (sin contar vacías)."""
        return [f for f in (self.cleaned_data.get("foto_1"), self.cleaned_data.get("foto_2")) if f]
