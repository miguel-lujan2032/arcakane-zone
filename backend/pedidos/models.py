from django.conf import settings
from django.db import models

from catalogo.models import Videojuego


class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PAGADO = "pagado", "Pagado"
        CANCELADO = "cancelado", "Cancelado"

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos",
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PENDIENTE
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-creado_en"]

    def __str__(self):
        return f"Pedido #{self.pk} — {self.cliente} [{self.estado}]"

    @property
    def total(self):
        return sum(d.subtotal for d in self.detalles.all())

    @property
    def puede_cancelar(self) -> bool:
        return self.estado == self.Estado.PENDIENTE


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="detalles")
    videojuego = models.ForeignKey(
        Videojuego, on_delete=models.PROTECT, related_name="detalles_pedido"
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Detalle de pedido"
        verbose_name_plural = "Detalles de pedido"
        unique_together = [("pedido", "videojuego")]

    def __str__(self):
        return f"{self.cantidad}x {self.videojuego} (Pedido #{self.pedido_id})"

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad
