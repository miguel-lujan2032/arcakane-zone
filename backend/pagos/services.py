import random
import uuid

from django.db import transaction

from pedidos.models import Pedido

from .models import Pago, Venta


@transaction.atomic
def procesar_pago_simulado(pedido: Pedido) -> tuple[bool, str]:
    """Simula la aprobación o rechazo de un pago y actualiza stock."""
    if pedido.estado != Pedido.Estado.PENDIENTE:
        return False, "El pedido no está en estado pendiente."

    # Verificar stock antes de procesar
    for detalle in pedido.detalles.select_related("videojuego").select_for_update():
        if detalle.videojuego.stock < detalle.cantidad:
            return False, f"Sin stock suficiente para '{detalle.videojuego.titulo}'."

    aprobado = random.random() < 0.9  # 90% de probabilidad de aprobación

    # Pago.pedido es OneToOne: si un intento anterior fue rechazado, se
    # reutiliza el registro en lugar de crear un duplicado (IntegrityError).
    pago, _ = Pago.objects.update_or_create(
        pedido=pedido,
        defaults={
            "monto": pedido.total,
            "estado": Pago.Estado.APROBADO if aprobado else Pago.Estado.RECHAZADO,
            "referencia": str(uuid.uuid4())[:8].upper(),
        },
    )

    if aprobado:
        # Descontar stock
        for detalle in pedido.detalles.select_related("videojuego"):
            videojuego = detalle.videojuego
            videojuego.stock -= detalle.cantidad
            videojuego.save(update_fields=["stock"])

        pedido.estado = Pedido.Estado.PAGADO
        pedido.save(update_fields=["estado"])

        Venta.objects.create(pedido=pedido, total=pedido.total)
        return True, f"¡Pago aprobado! Referencia: {pago.referencia}"

    return False, f"Pago rechazado (ref: {pago.referencia}). Intenta de nuevo."
