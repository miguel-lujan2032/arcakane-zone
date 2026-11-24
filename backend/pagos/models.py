from django.db import models
from django.db.models import Q

from pedidos.models import Pedido


class EstadoIntentoPago(models.Model):
    """
    Catálogo de estados de un intento de pago.

    ``codigo`` es el identificador estable referenciado por las filas de
    ``IntentoPago``; ``nombre`` es la etiqueta visible y editable. Regla de
    negocio: el resultado del pago no se almacena como enum en código (AZ-S1-17).
    """

    codigo = models.CharField(
        max_length=50,
        help_text="Identificador estable del estado; no es la etiqueta visible.",
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Estado de intento de pago"
        verbose_name_plural = "Estados de intento de pago"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                name="pagos_estadointentopago_codigo_unico",
            ),
        ]

    def __str__(self):
        return self.nombre


class IntentoPago(models.Model):
    """
    Intento de pago asociado a un pedido (AZ-S1-19).

    Regla de negocio: un pedido puede tener múltiples intentos (p. ej. tras un
    rechazo), pero cada intento conserva su importe, referencia interna e
    identidad de idempotencia para trazabilidad; no se almacenan datos de
    tarjetas ni credenciales financieras.
    """

    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.PROTECT,
        related_name="intentos_pago",
        help_text="Pedido al que pertenece el intento (permite varios intentos).",
    )
    importe = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Importe del intento (snapshot monetario del intento).",
    )
    estado = models.ForeignKey(
        EstadoIntentoPago,
        to_field="codigo",
        db_column="estado",
        db_index=False,
        on_delete=models.PROTECT,
        related_name="intentos_pago",
        default="pendiente",
        help_text="Resultado del intento de pago (catálogo pagos.EstadoIntentoPago).",
    )
    referencia = models.CharField(
        max_length=100,
        help_text="Referencia interna única del intento (identidad trazable).",
    )
    clave_idempotencia = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Clave de idempotencia del intento; única cuando está presente.",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Intento de pago"
        verbose_name_plural = "Intentos de pago"
        constraints = [
            # Regla de negocio: un intento no puede tener importe negativo.
            models.CheckConstraint(
                condition=Q(importe__gte=0),
                name="pagos_intento_importe_nn",
            ),
            # Regla de negocio: la referencia interna identifica de forma única el intento.
            models.UniqueConstraint(
                fields=["referencia"],
                name="pagos_intento_ref_unico",
            ),
            # Regla de negocio: la clave de idempotencia no se repite cuando se informa.
            models.UniqueConstraint(
                fields=["clave_idempotencia"],
                condition=~Q(clave_idempotencia=""),
                name="pagos_intento_idem_unico",
            ),
        ]
        indexes = [
            # Historial de intentos de un pedido, del más reciente al más antiguo.
            models.Index(
                fields=["pedido", "-creado_en"],
                name="pagos_intento_ped_fec_idx",
            ),
            # Consultas operativas por estado y fecha.
            models.Index(
                fields=["estado", "-creado_en"],
                name="pagos_intento_est_fec_idx",
            ),
        ]

    def __str__(self):
        return f"Intento #{self.pk} — Pedido #{self.pedido_id} [{self.estado_id}]"


class Venta(models.Model):
    """
    Venta consolidada de un pedido completado (AZ-S1-19).

    Regla de negocio: una venta es 1:1 con el pedido y referencia de forma
    protegida al intento aprobado que la originó; ``total`` es un snapshot
    contable (verificable contra la suma de detalles en el momento de la venta).
    """

    pedido = models.OneToOneField(Pedido, on_delete=models.PROTECT, related_name="venta")
    intento_aprobado = models.OneToOneField(
        IntentoPago,
        on_delete=models.PROTECT,
        related_name="venta_generada",
        help_text="Intento de pago aprobado que originó la venta (trazabilidad protegida).",
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    registrada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        constraints = [
            # Regla de negocio: el total consolidado de una venta no puede ser negativo.
            models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name="pagos_venta_total_no_negativo",
            ),
        ]
        indexes = [
            # Reportes de ventas ordenados por fecha de registro.
            models.Index(
                fields=["registrada_en"],
                name="pagos_venta_registrada_idx",
            ),
        ]

    def __str__(self):
        return f"Venta #{self.pk} — Pedido #{self.pedido_id} (${self.total})"
