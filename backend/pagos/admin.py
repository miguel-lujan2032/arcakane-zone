from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import IntentoPago, Venta


@admin.register(IntentoPago)
class IntentoPagoAdmin(ModelAdmin):
    list_display = ["id", "pedido", "importe", "estado", "referencia", "creado_en"]
    list_filter = ["estado"]
    search_fields = ["pedido__id", "referencia", "clave_idempotencia"]
    readonly_fields = ["creado_en", "actualizado_en"]


@admin.register(Venta)
class VentaAdmin(ModelAdmin):
    list_display = ["id", "pedido", "intento_aprobado", "total", "registrada_en"]
    search_fields = ["pedido__id", "intento_aprobado__referencia"]
    readonly_fields = ["registrada_en"]
    date_hierarchy = "registrada_en"
