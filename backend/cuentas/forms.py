from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm

from .models import Rol, Usuario

_INPUT = {"class": "w-full"}
_TEXTAREA = {"class": "w-full", "rows": "3"}


class RegistroForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ["username", "email", "first_name", "last_name", "password1", "password2"]

    def save(self, commit=True):
        usuario = super().save(commit=False)
        rol_cliente, _ = Rol.objects.get_or_create(nombre="cliente")
        usuario.rol = rol_cliente
        if commit:
            usuario.save()
        return usuario


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "email", "telefono", "direccion"]
        widgets = {
            "first_name": forms.TextInput(attrs={**_INPUT, "placeholder": "Nombre"}),
            "last_name": forms.TextInput(attrs={**_INPUT, "placeholder": "Apellido"}),
            "email": forms.EmailInput(attrs={**_INPUT, "placeholder": "correo@ejemplo.com"}),
            "telefono": forms.TextInput(attrs={**_INPUT, "placeholder": "Ej. 310 123 4567"}),
            "direccion": forms.Textarea(attrs={**_TEXTAREA, "placeholder": "Dirección de envío (opcional)"}),
        }
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellido",
            "email": "Correo electrónico",
            "telefono": "Teléfono / WhatsApp",
            "direccion": "Dirección",
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        qs = Usuario.objects.filter(email=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe una cuenta con ese correo electrónico.")
        return email


class CambioPasswordForm(PasswordChangeForm):
    """Wrapper de PasswordChangeForm con widgets estilizados y labels en español."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "w-full"})
        self.fields["old_password"].label = "Contraseña actual"
        self.fields["new_password1"].label = "Nueva contraseña"
        self.fields["new_password2"].label = "Confirmar nueva contraseña"
