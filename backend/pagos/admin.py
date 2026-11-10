from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Pago, Venta


@admin.register(Pago)
class PagoAdmin(ModelAdmin):
    list_display = ["id", "pedido", "monto", "estado", "referencia", "creado_en"]
    list_filter = ["estado"]
    search_fields = ["pedido__id", "referencia"]
    readonly_fields = ["creado_en"]


@admin.register(Venta)
class VentaAdmin(ModelAdmin):
    list_display = ["id", "pedido", "total", "registrada_en"]
    search_fields = ["pedido__id"]
    readonly_fields = ["registrada_en"]
    date_hierarchy = "registrada_en"
