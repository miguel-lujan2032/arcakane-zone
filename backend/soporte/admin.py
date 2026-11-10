from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Contacto


@admin.register(Contacto)
class ContactoAdmin(ModelAdmin):
    list_display = ["asunto", "nombre", "email", "telefono", "atendido", "creado_en"]
    list_filter = ["atendido"]
    search_fields = ["nombre", "email", "asunto"]
    readonly_fields = ["creado_en"]
    list_editable = ["atendido"]
