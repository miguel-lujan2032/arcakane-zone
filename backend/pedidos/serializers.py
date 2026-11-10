from rest_framework import serializers

from catalogo.serializers import VideojuegoResumenSerializer

from .models import DetallePedido, Pedido


class DetallePedidoSerializer(serializers.ModelSerializer):
    videojuego = VideojuegoResumenSerializer(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = DetallePedido
        fields = ["id", "videojuego", "cantidad", "precio_unitario", "subtotal"]


class PedidoSerializer(serializers.ModelSerializer):
    cliente = serializers.CharField(source="cliente.username", read_only=True)
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    puede_cancelar = serializers.BooleanField(read_only=True)

    class Meta:
        model = Pedido
        fields = [
            "id",
            "cliente",
            "estado",
            "estado_display",
            "detalles",
            "total",
            "puede_cancelar",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = [
            "id",
            "cliente",
            "estado",
            "estado_display",
            "detalles",
            "total",
            "puede_cancelar",
            "creado_en",
            "actualizado_en",
        ]


class AgregarItemSerializer(serializers.Serializer):
    videojuego_id = serializers.IntegerField(min_value=1)
    cantidad = serializers.IntegerField(min_value=1, default=1)


class ActualizarItemSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField()
