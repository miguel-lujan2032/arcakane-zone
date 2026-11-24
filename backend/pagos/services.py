import random
import uuid

from django.db import transaction

from catalogo.models import OfertaVideojuego
from pedidos.models import Pedido

from .models import IntentoPago, Venta


@transaction.atomic
def procesar_pago_simulado(pedido: Pedido) -> tuple[bool, str]:
    """Simula la aprobación o rechazo de un pago y actualiza stock de las ofertas."""
    if pedido.estado_id != "pendiente":
        return False, "El pedido no está en estado pendiente."

    # Bloquear las ofertas antes de verificar y descontar stock.
    ofertas_ids = list(pedido.detalles.values_list("oferta_id", flat=True))
    ofertas = {
        o.pk: o
        for o in OfertaVideojuego.objects.select_for_update().filter(pk__in=ofertas_ids)
    }
    detalles = pedido.detalles.select_related("oferta__videojuego").all()

    for detalle in detalles:
        oferta = ofertas[detalle.oferta_id]
        if oferta.stock < detalle.cantidad:
            return False, f"Sin stock suficiente para '{detalle.titulo_snapshot}'."

    aprobado = random.random() < 0.9  # 90% de probabilidad de aprobación
    referencia = str(uuid.uuid4())[:8].upper()

    intento = IntentoPago.objects.create(
        pedido=pedido,
        importe=pedido.total,
        estado_id="aprobado" if aprobado else "rechazado",
        referencia=referencia,
        clave_idempotencia="",
    )

    if aprobado:
        # Descontar stock de cada oferta
        for detalle in detalles:
            oferta = ofertas[detalle.oferta_id]
            oferta.stock -= detalle.cantidad
            oferta.save(update_fields=["stock"])

        pedido.estado_id = "pagado"
        pedido.save(update_fields=["estado"])

        Venta.objects.create(
            pedido=pedido, intento_aprobado=intento, total=pedido.total
        )
        return True, f"¡Pago aprobado! Referencia: {intento.referencia}"

    return False, f"Pago rechazado (ref: {intento.referencia}). Intenta de nuevo."
