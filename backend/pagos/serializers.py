from rest_framework import serializers

from .models import Pago, Venta


class PagoSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Pago
        fields = [
            "id",
            "pedido",
            "monto",
            "estado",
            "estado_display",
            "referencia",
            "creado_en",
        ]
        read_only_fields = fields


class VentaSerializer(serializers.ModelSerializer):
    pedido_id = serializers.IntegerField(source="pedido.id", read_only=True)
    cliente = serializers.CharField(source="pedido.cliente.username", read_only=True)

    class Meta:
        model = Venta
        fields = ["id", "pedido_id", "cliente", "total", "registrada_en"]
        read_only_fields = fields
