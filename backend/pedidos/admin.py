from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import DetallePedido, Pedido


class DetallePedidoInline(TabularInline):
    model = DetallePedido
    extra = 0
    readonly_fields = ["subtotal"]


@admin.register(Pedido)
class PedidoAdmin(ModelAdmin):
    list_display = ["id", "cliente", "estado", "total", "creado_en"]
    list_filter = ["estado"]
    search_fields = ["cliente__username", "cliente__email"]
    readonly_fields = ["total", "creado_en", "actualizado_en"]
    inlines = [DetallePedidoInline]
    date_hierarchy = "creado_en"
