from rest_framework import serializers

from catalogo.models import Videojuego
from pagos.models import Venta


class ReporteVideojuegoSerializer(serializers.ModelSerializer):
    categoria = serializers.CharField(source="categoria.nombre", read_only=True)
    plataforma = serializers.CharField(source="plataforma.nombre", read_only=True)
    genero = serializers.CharField(source="genero.nombre", read_only=True)
    disponible = serializers.BooleanField(read_only=True)

    class Meta:
        model = Videojuego
        fields = [
            "id",
            "titulo",
            "precio",
            "stock",
            "activo",
            "disponible",
            "categoria",
            "plataforma",
            "genero",
            "fecha_lanzamiento",
        ]
        read_only_fields = fields


class VentaReporteSerializer(serializers.ModelSerializer):
    pedido_id = serializers.IntegerField(source="pedido.id", read_only=True)
    cliente = serializers.CharField(source="pedido.cliente.username", read_only=True)
    detalles = serializers.SerializerMethodField()

    class Meta:
        model = Venta
        fields = ["id", "pedido_id", "cliente", "total", "registrada_en", "detalles"]
        read_only_fields = fields

    def get_detalles(self, obj):
        return [
            {
                "videojuego": detalle.videojuego.titulo,
                "cantidad": detalle.cantidad,
                "precio_unitario": str(detalle.precio_unitario),
                "subtotal": str(detalle.subtotal),
            }
            for detalle in obj.pedido.detalles.select_related("videojuego").all()
        ]


class InventarioSerializer(serializers.ModelSerializer):
    categoria = serializers.CharField(source="categoria.nombre", read_only=True)
    plataforma = serializers.CharField(source="plataforma.nombre", read_only=True)
    genero = serializers.CharField(source="genero.nombre", read_only=True)

    class Meta:
        model = Videojuego
        fields = [
            "id",
            "titulo",
            "stock",
            "activo",
            "precio",
            "categoria",
            "plataforma",
            "genero",
        ]
        read_only_fields = fields


__all__ = [
    "InventarioSerializer",
    "ReporteVideojuegoSerializer",
    "VentaReporteSerializer",
]
