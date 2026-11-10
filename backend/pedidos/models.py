from django.conf import settings
from django.db import models

from catalogo.models import OfertaVideojuego


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
    """
    Línea de pedido que referencia la oferta adquirida.

    El detalle congela el precio unitario cobrado y un snapshot del
    título y la plataforma al momento de la compra: los detalles
    históricos no cambian aunque el catálogo se modifique después.
    """

    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="detalles"
    )
    oferta = models.ForeignKey(
        OfertaVideojuego,
        on_delete=models.PROTECT,
        related_name="detalles_pedido",
    )
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    titulo_snapshot = models.CharField(max_length=200)
    plataforma_snapshot = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Detalle de pedido"
        verbose_name_plural = "Detalles de pedido"
        constraints = [
            models.UniqueConstraint(
                fields=["pedido", "oferta"],
                name="pedidos_detallepedido_pedido_oferta_unicos",
            ),
        ]

    def __str__(self):
        return f"{self.cantidad}x {self.titulo_snapshot} (Pedido #{self.pedido_id})"

    def save(self, *args, **kwargs):
        """Congela el snapshot del título/plataforma solo al crear la línea."""
        if self._state.adding:
            if not self.titulo_snapshot:
                self.titulo_snapshot = self.oferta.videojuego.titulo
            if not self.plataforma_snapshot:
                self.plataforma_snapshot = self.oferta.plataforma.nombre
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad
