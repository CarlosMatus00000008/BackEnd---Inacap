import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import Group
from django.utils import timezone

from core.formularios import FormularioBase, TextoField
from viajes.senales import GRUPO_VIAJEROS

from .models import PerfilUsuario

Usuario = get_user_model()


class CorreoUnicoMixin:
    """Valida que el correo no esté registrado por otra cuenta (sin distinguir mayúsculas)."""

    def clean_email(self):
        correo = self.cleaned_data["email"].strip().lower()
        otros = Usuario.objects.filter(email__iexact=correo)
        if self.instance.pk:
            otros = otros.exclude(pk=self.instance.pk)
        if otros.exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return correo


class TelefonoField(forms.CharField):
    """
    Teléfono opcional. Acepta «+56 9 1234 5678», «9 1234 5678», «(2) 2345 6789»…
    y lo guarda normalizado: «+56912345678». Sin prefijo se asume Chile (+56).
    """

    widget = forms.TextInput(attrs={"type": "tel", "inputmode": "tel", "autocomplete": "tel"})
    mensaje = "Ingresa un teléfono válido, por ejemplo +56 9 1234 5678."

    def to_python(self, value):
        valor = super().to_python(value)
        if not valor:
            return valor
        digitos = re.sub(r"[\s.\-()]", "", valor)
        if digitos.startswith("+"):
            numero = digitos
        elif len(digitos) == 9:
            numero = "+56" + digitos
        else:
            numero = "+" + digitos
        if not re.fullmatch(r"\+\d{8,15}", numero) or (numero.startswith("+56") and len(numero) != 12):
            raise forms.ValidationError(self.mensaje, code="telefono_invalido")
        return numero


class RegistroForm(FormularioBase, CorreoUnicoMixin, UserCreationForm):
    email = forms.EmailField(label="Correo electrónico", max_length=254)
    first_name = TextoField(label="Nombre", max_length=150, required=False)
    telefono = TelefonoField(
        label="Teléfono",
        max_length=20,
        required=False,
        help_text="Opcional. Ejemplo: +56 9 1234 5678",
    )
    # Consentimiento (Ley N° 19.628 y N° 21.719): obligatorio y desmarcado por defecto.
    acepta_datos = forms.BooleanField(
        label="Autorizo el tratamiento de mis datos personales conforme a la Ley N° 19.628 sobre Protección de Datos Personales.",
        required=True,
        initial=False,
        error_messages={"required": "Debes autorizar el tratamiento de tus datos personales para continuar."},
        template_name="cuentas/_campo_consentimiento.html",
    )

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("username", "first_name", "email")
        labels = {"username": "Nombre de usuario"}
        help_texts = {"username": "Hasta 150 caracteres: letras, números y @ . + - _"}

    field_order = ("username", "first_name", "email", "telefono", "password1", "password2", "acepta_datos")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(autocomplete="username", autofocus=True)
        self.fields["email"].widget.attrs.update(autocomplete="email")
        self.fields["first_name"].widget.attrs.update(autocomplete="given-name")

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        if commit:
            # Todo usuario nuevo entra al grupo «Viajeros» (permisos para usar el diario).
            grupo, _ = Group.objects.get_or_create(name=GRUPO_VIAJEROS)
            usuario.groups.add(grupo)
            PerfilUsuario.objects.update_or_create(
                usuario=usuario,
                defaults={"telefono": self.cleaned_data.get("telefono", ""), "acepta_datos": True, "fecha_consentimiento": timezone.now()},
            )
        return usuario


class IngresoForm(FormularioBase, AuthenticationForm):
    error_messages = {
        "invalid_login": "Usuario o contraseña incorrectos. Revisa mayúsculas y minúsculas.",
        "inactive": "Esta cuenta está desactivada.",
    }


class PerfilForm(FormularioBase, CorreoUnicoMixin, forms.ModelForm):
    first_name = TextoField(label="Nombre", max_length=150, required=False)
    last_name = TextoField(label="Apellido", max_length=150, required=False)
    email = forms.EmailField(label="Correo electrónico", max_length=254)

    class Meta:
        model = Usuario
        fields = ("first_name", "last_name", "email")


class CambioContrasenaForm(FormularioBase, PasswordChangeForm):
    pass
