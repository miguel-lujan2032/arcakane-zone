from django import forms

from .models import Contacto

_ATTRS_INPUT = {"class": "w-full"}
_ATTRS_TEXTAREA = {"class": "w-full", "rows": "5"}


class ContactoForm(forms.ModelForm):
    class Meta:
        model = Contacto
        fields = ["nombre", "email", "asunto", "mensaje"]
        widgets = {
            "nombre": forms.TextInput(attrs={**_ATTRS_INPUT, "placeholder": "Tu nombre completo"}),
            "email": forms.EmailInput(attrs={**_ATTRS_INPUT, "placeholder": "tucorreo@ejemplo.com"}),
            "asunto": forms.TextInput(attrs={**_ATTRS_INPUT, "placeholder": "Asunto del mensaje"}),
            "mensaje": forms.Textarea(attrs={**_ATTRS_TEXTAREA, "placeholder": "Escribe tu mensaje aquí…"}),
        }
        labels = {
            "nombre": "Nombre",
            "email": "Correo electrónico",
            "asunto": "Asunto",
            "mensaje": "Mensaje",
        }


class MayorInformacionForm(forms.ModelForm):
    class Meta:
        model = Contacto
        fields = ["nombre", "email", "telefono"]
        widgets = {
            "nombre": forms.TextInput(attrs={**_ATTRS_INPUT, "placeholder": "Tu nombre completo"}),
            "email": forms.EmailInput(attrs={**_ATTRS_INPUT, "placeholder": "tucorreo@ejemplo.com"}),
            "telefono": forms.TextInput(attrs={**_ATTRS_INPUT, "placeholder": "Ej. 310 123 4567 (opcional)"}),
        }
        labels = {
            "nombre": "Nombre",
            "email": "Correo electrónico",
            "telefono": "Teléfono / WhatsApp",
        }
