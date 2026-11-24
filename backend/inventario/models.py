"""
Libro mayor de movimientos de inventario (AZ-S1-14).

Estrategia de ledger elegida: **saldos corridos congelados por movimiento**
(running balances). Cada movimiento registra la cantidad operada y el saldo
de la oferta ANTES y DESPUÉS de aplicarla, por lo que el historial de una
oferta es verificable punto a punto sin recalcular nada:

    saldo(n) = saldo_anterior(n)
    saldo(n) = saldo_posterior(n-1)   (continuidad de la cadena)

La relación aritmética entre ``saldo_anterior``, ``cantidad`` y
``saldo_posterior`` depende del signo del movimiento, que vive en el
catálogo (``tipo_movimiento.naturaleza``) y por eso NO es expresable como
un ``CheckConstraint`` de base de datos. Los invariantes que la capa de
datos sí garantiza son:

    cantidad > 0
    saldo_anterior >= 0
    saldo_posterior >= 0
    clave de idempotencia única
    detalle de pedido referenciado a lo sumo por un movimiento

La validación de la continuidad/aritmética corresponde a los servicios que
escriben el ledger (fuera de alcance de este issue), bajo el contrato:

    with transaction.atomic():
        oferta = OfertaVideojuego.objects.select_for_update().get(...)
        saldo = oferta.stock
        # validar saldo_posterior = saldo ± cantidad según naturaleza
        MovimientoInventarioOfertaVideojuego.objects.create(...)
        oferta.stock = saldo_posterior
        oferta.save(update_fields=["stock"])

El movimiento es INMUTABLE: no se modifica ni se elimina desde operaciones
ordinarias; las correcciones se registran como movimientos compensatorios
nuevos que referencian al original (``movimiento_compensado``).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class RegistroInmutableError(Exception):
    """Se intentó mutar un registro del libro mayor (inmutable)."""


class QuerySetInmutable(models.QuerySet):
    """
    QuerySet que rechaza mutaciones masivas sobre registros inmutables.

    Solo se permiten operaciones de lectura y de creación (``create``,
    ``bulk_create``, filtros, agregaciones...). ``update``, ``bulk_update``
    y ``delete`` están bloqueados para que ninguna vía del ORM pueda
    reescribir la historia.
    """

    def update(self, **kwargs):  # noqa: A003 - firma de Django
        raise RegistroInmutableError(
            "El libro mayor es inmutable: no se puede actualizar en lote. "
            "Registre un movimiento compensatorio."
        )

    def bulk_update(self, objs, fields, batch_size=None):
        raise RegistroInmutableError(
            "El libro mayor es inmutable: no se puede actualizar en lote. "
            "Registre un movimiento compensatorio."
        )

    def delete(self):
        raise RegistroInmutableError(
            "El libro mayor es inmutable: no se puede eliminar en lote."
        )


class ModeloInmutable(models.Model):
    """
    Contrato de inmutabilidad para modelos de solo-apéndice.

    Cualquier modelo que herede de esta base cumple el mismo contrato
    (sustituibilidad de Liskov): sus filas se crean una vez y jamás se
    modifican ni se eliminan a través del ORM. ``bulk_create`` sigue
    siendo válido porque solo inserta.
    """

    objects = QuerySetInmutable.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Permite insertar; rechaza cualquier actualización."""
        if not self._state.adding:
            raise RegistroInmutableError(
                "Los registros del libro mayor no se modifican: registre un "
                "movimiento compensatorio nuevo."
            )
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        """El historial nunca se borra desde el ORM."""
        raise RegistroInmutableError(
            "Los registros del libro mayor no se eliminan."
        )


class TipoMovimientoInventario(models.Model):
    """
    Catálogo de tipos de movimiento de inventario.

    Es una tabla relacional, no un enum: agregar un tipo nuevo es insertar
    una fila, sin cambios de código ni de esquema (abierto/cerrado). La
    ``naturaleza`` es un dato de la fila y determina cómo derivar el efecto
    sobre el saldo:

      - ``entrada``: saldo_posterior = saldo_anterior + cantidad
      - ``salida``:  saldo_posterior = saldo_anterior - cantidad
      - ``ajuste``:  saldo_posterior = cantidad (el conteo fija el saldo)
    """

    class Naturaleza(models.TextChoices):
        ENTRADA = "entrada", "Entrada"
        SALIDA = "salida", "Salida"
        AJUSTE = "ajuste", "Ajuste"

    codigo = models.CharField(
        max_length=50,
        help_text="Identificador estable del tipo (p. ej. ENTRADA, SALIDA).",
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    naturaleza = models.CharField(max_length=10, choices=Naturaleza.choices)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Tipo de movimiento de inventario"
        verbose_name_plural = "Tipos de movimiento de inventario"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                name="inventario_tipomovimiento_codigo_unico",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} [{self.codigo}]"


class MotivoMovimientoInventario(models.Model):
    """
    Catálogo de motivos controlados de un movimiento (VENTA, DEVOLUCION...).

    Tabla relacional con las mismas reglas que el tipo: ``codigo`` único y
    estable. El texto libre no controlado va en la ``observacion`` del
    propio movimiento, no aquí.
    """

    codigo = models.CharField(
        max_length=50,
        help_text="Identificador estable del motivo (p. ej. VENTA).",
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Motivo de movimiento de inventario"
        verbose_name_plural = "Motivos de movimiento de inventario"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                name="inventario_motivomovimiento_codigo_unico",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} [{self.codigo}]"


class MovimientoInventarioOfertaVideojuego(ModeloInmutable):
    """
    Movimiento del libro mayor de inventario de una oferta (unidad vendible).

    Referencia por cadenas ("app.Modelo") a oferta, usuario y detalle de
    pedido para no acoplar el módulo a implementaciones concretas ni crear
    imports circulares (inversión de dependencias).

    Semántica de campos:
      - ``oferta``: la unidad comercial vendible; el videojuego genérico
        NO es nivel de inventario.
      - ``cantidad``/``unidad``: magnitud operada (estrictamente positiva)
        y su unidad de medida. No existe catálogo de unidades en el repo:
        ``unidad`` es un campo de texto con valor por defecto "unidad"
        (licencias/copias), consistente con ``OfertaVideojuego.stock``.
      - ``saldo_anterior``/``saldo_posterior``: saldo corrido congelado
        antes y después del movimiento (estrategia de ledger del módulo).
      - ``fecha_hora``: momento del registro, autogenerado y no editable.
      - ``usuario_responsable``: null representa un proceso del sistema;
        PROTECT para que la autoría histórica no pueda borrarse.
      - ``detalle_pedido``: referencia única opcional a la línea que
        origina una salida por venta (trazabilidad venta → movimiento).
      - ``clave_idempotencia``: identificador de idempotencia provisto por
        el servicio escritor; la BD rechaza duplicados.
      - ``movimiento_compensado``: movimiento original que este registro
        corrige (las correcciones son movimientos nuevos, nunca ediciones).
    """

    oferta = models.ForeignKey(
        "catalogo.OfertaVideojuego",
        on_delete=models.PROTECT,
        related_name="movimientos_inventario",
    )
    tipo_movimiento = models.ForeignKey(
        TipoMovimientoInventario,
        on_delete=models.PROTECT,
        related_name="movimientos",
    )
    motivo = models.ForeignKey(
        MotivoMovimientoInventario,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos",
    )
    observacion = models.TextField(blank=True)
    cantidad = models.PositiveIntegerField()
    unidad = models.CharField(max_length=50, default="unidad")
    saldo_anterior = models.PositiveIntegerField()
    saldo_posterior = models.PositiveIntegerField()
    fecha_hora = models.DateTimeField(default=timezone.now, editable=False)
    usuario_responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_inventario",
    )
    detalle_pedido = models.ForeignKey(
        "pedidos.DetallePedido",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimiento_inventario",
    )
    clave_idempotencia = models.CharField(max_length=200)
    movimiento_compensado = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="movimientos_compensatorios",
    )

    class Meta:
        verbose_name = "Movimiento de inventario de oferta"
        verbose_name_plural = "Movimientos de inventario de ofertas"
        ordering = ["fecha_hora", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["clave_idempotencia"],
                name="inventario_movimiento_clave_idempotencia_unica",
            ),
            # Un detalle de pedido origina a lo sumo UN movimiento: los
            # movimientos de sistema/tienda (detalle null) son libres.
            models.UniqueConstraint(
                fields=["detalle_pedido"],
                condition=models.Q(detalle_pedido__isnull=False),
                name="inventario_movimiento_detalle_pedido_unico",
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="inventario_movimiento_cantidad_positiva",
            ),
            models.CheckConstraint(
                condition=models.Q(saldo_anterior__gte=0),
                name="inventario_movimiento_saldo_anterior_no_negativo",
            ),
            models.CheckConstraint(
                condition=models.Q(saldo_posterior__gte=0),
                name="inventario_movimiento_saldo_posterior_no_negativo",
            ),
        ]
        indexes = [
            # Historial de una oferta, del más reciente al más antiguo.
            models.Index(
                fields=["oferta", "-fecha_hora"],
                name="inventario_oferta_fecha_idx",
            ),
            # Consultas operativas por tipo (p. ej. salidas recientes).
            models.Index(
                fields=["tipo_movimiento", "-fecha_hora"],
                name="inventario_mov_tipo_fecha_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.tipo_movimiento.codigo} {self.cantidad} "
            f"«{self.oferta}» ({self.saldo_anterior}→{self.saldo_posterior})"
        )
