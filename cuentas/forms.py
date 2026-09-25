from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import Group

from core.formularios import FormularioBase, TextoField
from viajes.senales import GRUPO_VIAJEROS

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


class RegistroForm(FormularioBase, CorreoUnicoMixin, UserCreationForm):
    email = forms.EmailField(label="Correo electrónico", max_length=254)
    first_name = TextoField(label="Nombre", max_length=150, required=False)

    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("username", "first_name", "email")
        labels = {"username": "Nombre de usuario"}
        help_texts = {"username": "Hasta 150 caracteres: letras, números y @ . + - _"}

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
