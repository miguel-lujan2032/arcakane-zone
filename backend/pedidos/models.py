from django.conf import settings
from django.db import models
from django.utils import timezone

from catalogo.models import OfertaVideojuego
from inventario.models import ModeloInmutable


class EstadoPedido(models.Model):
    """
    Catálogo de estados de un pedido.

    Tabla relacional: ``codigo`` es el identificador estable que referencian
    las filas transaccionales; ``nombre`` es la etiqueta visible y editable sin
    alterar el historial. Regla de negocio: el dominio de estados no es un enum
    en código (AZ-S1-17).
    """

    codigo = models.CharField(
        max_length=50,
        help_text="Identificador estable del estado; no es la etiqueta visible.",
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Estado de pedido"
        verbose_name_plural = "Estados de pedido"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                name="pedidos_estadopedido_codigo_unico",
            ),
        ]

    def __str__(self):
        return self.nombre


class Pedido(models.Model):
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pedidos",
    )
    estado = models.ForeignKey(
        EstadoPedido,
        to_field="codigo",
        db_column="estado",
        db_index=False,
        on_delete=models.PROTECT,
        related_name="pedidos",
        default="pendiente",
        help_text="Estado actual del pedido (catálogo pedidos.EstadoPedido).",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-creado_en"]
        indexes = [
            # Historial de compras de un cliente, del más reciente al más antiguo.
            models.Index(
                fields=["cliente", "-creado_en"],
                name="pedidos_pedido_cli_fecha_idx",
            ),
        ]

    def __str__(self):
        return f"Pedido #{self.pk} — {self.cliente} [{self.estado_id}]"

    @property
    def total(self):
        return sum(d.subtotal for d in self.detalles.all())

    @property
    def puede_cancelar(self) -> bool:
        return self.estado_id == "pendiente"

    @property
    def pago(self):
        """Compatibilidad de solo lectura: intento de pago aprobado del pedido (o None)."""
        # related_name dinámico tras normalización: intentos_pago (FK 1:N).
        if not self.pk:
            return None
        manager = getattr(self, "intentos_pago", None)
        if manager is None:
            return None
        return manager.filter(estado_id="aprobado").order_by("-creado_en", "-pk").first()


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
            # Regla de negocio: una línea siempre representa al menos una
            # unidad comprada; no existen líneas de cantidad cero o negativa.
            models.CheckConstraint(
                condition=models.Q(cantidad__gte=1),
                name="pedidos_detallepedido_cantidad_positiva",
            ),
            # Regla de negocio: el precio congelado de la línea no puede ser
            # negativo (una devolución no se modela como precio negativo).
            models.CheckConstraint(
                condition=models.Q(precio_unitario__gte=0),
                name="pedidos_detallepedido_precio_unitario_no_negativo",
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


class HistorialEstadoPedido(ModeloInmutable):
    """
    Historial inmutable de cambios de estado de un pedido (AZ-S1-19).

    Regla de negocio: cada transición/estado relevante queda registrado y no se
    modifica ni se elimina; el historial se preserva aunque cambien catálogos o
    procesos. La escritura automática en cada transición es responsabilidad del
    servicio (deuda técnica); este modelo garantiza la conservación en datos.
    """

    pedido = models.ForeignKey(
        "pedidos.Pedido",
        on_delete=models.PROTECT,
        related_name="historial_estados",
        help_text="Pedido cuyo cambio de estado se registra.",
    )
    estado = models.ForeignKey(
        "pedidos.EstadoPedido",
        to_field="codigo",
        db_column="estado",
        db_index=False,
        on_delete=models.PROTECT,
        related_name="historial_pedidos",
        help_text="Estado del pedido en este registro histórico (catálogo).",
    )
    fecha = models.DateTimeField(
        default=timezone.now,
        editable=False,
        help_text="Momento del registro del estado.",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cambios_estado_pedido",
        help_text="Usuario responsable; NULL si fue el sistema o una migración.",
    )
    observacion = models.TextField(
        blank=True,
        help_text="Observación o motivo asociado al registro.",
    )

    class Meta:
        verbose_name = "Historial de estado de pedido"
        verbose_name_plural = "Historial de estados de pedido"
        ordering = ["fecha", "pk"]
        indexes = [
            # Historial cronológico de un pedido.
            models.Index(
                fields=["pedido", "fecha"],
                name="pedidos_hist_ped_fec_idx",
            ),
        ]

    def __str__(self):
        return f"Pedido #{self.pedido_id} → {self.estado_id} ({self.fecha:%Y-%m-%d %H:%M})"
