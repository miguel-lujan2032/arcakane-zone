from django.db import transaction

from catalogo.models import OfertaVideojuego

from .models import DetallePedido, Pedido


def get_or_create_carrito(usuario) -> Pedido:
    pedido, _ = Pedido.objects.get_or_create(
        cliente=usuario, estado=Pedido.Estado.PENDIENTE
    )
    return pedido


def validar_para_checkout(pedido: Pedido) -> list[str]:
    """
    Valida que el carrito esté listo para confirmar el pedido.
    Retorna lista de errores (vacía = todo OK).
    """
    errores = []
    detalles = pedido.detalles.select_related(
        "oferta__videojuego", "oferta__plataforma"
    ).all()

    if not detalles.exists():
        errores.append("El carrito está vacío.")
        return errores

    for detalle in detalles:
        oferta = detalle.oferta
        if not oferta.esta_publicada:
            errores.append(f'"{detalle.titulo_snapshot}" ya no está disponible.')
        elif oferta.stock < detalle.cantidad:
            errores.append(
                f'"{detalle.titulo_snapshot}": stock insuficiente '
                f"(tienes {detalle.cantidad} en el carrito, quedan {oferta.stock})."
            )
    return errores


@transaction.atomic
def agregar_o_incrementar(usuario, oferta_id: int, cantidad: int = 1) -> tuple[bool, str]:
    """Agrega una oferta al carrito o incrementa su cantidad. Valida stock."""
    try:
        oferta = (
            OfertaVideojuego.objects.select_for_update()
            .select_related("videojuego", "plataforma")
            .get(pk=oferta_id)
        )
    except OfertaVideojuego.DoesNotExist:
        return False, "Oferta no encontrada."

    if not oferta.esta_publicada:
        return False, f'"{oferta.videojuego.titulo}" ya no está publicada.'
    if oferta.stock <= 0:
        return False, f'"{oferta.videojuego.titulo}" no tiene stock disponible.'

    pedido = get_or_create_carrito(usuario)
    detalle, creado = DetallePedido.objects.get_or_create(
        pedido=pedido,
        oferta=oferta,
        defaults={"precio_unitario": oferta.precio_vigente, "cantidad": 0},
    )

    nueva_cantidad = detalle.cantidad + cantidad
    if nueva_cantidad > oferta.stock:
        return False, f'Stock insuficiente. Máximo disponible: {oferta.stock}.'

    detalle.cantidad = nueva_cantidad
    detalle.save(update_fields=["cantidad"])
    return True, (
        f'"{oferta.videojuego.titulo}" ({oferta.plataforma.nombre}) '
        "agregado al carrito."
    )


@transaction.atomic
def actualizar_cantidad(usuario, detalle_id: int, cantidad: int) -> tuple[bool, str]:
    """Cambia la cantidad de un ítem. Si cantidad <= 0, lo elimina."""
    try:
        detalle = (
            DetallePedido.objects.select_for_update()
            .select_related("oferta")
            .get(
                pk=detalle_id,
                pedido__cliente=usuario,
                pedido__estado=Pedido.Estado.PENDIENTE,
            )
        )
    except DetallePedido.DoesNotExist:
        return False, "Ítem no encontrado."

    if cantidad <= 0:
        detalle.delete()
        return True, "Ítem eliminado del carrito."

    stock = detalle.oferta.stock
    if cantidad > stock:
        return False, f'Stock insuficiente. Máximo disponible: {stock}.'

    detalle.cantidad = cantidad
    detalle.save(update_fields=["cantidad"])
    return True, "Cantidad actualizada."


@transaction.atomic
def quitar_item(usuario, detalle_id: int) -> tuple[bool, str]:
    try:
        detalle = DetallePedido.objects.get(
            pk=detalle_id, pedido__cliente=usuario, pedido__estado=Pedido.Estado.PENDIENTE
        )
        detalle.delete()
        return True, "Ítem eliminado."
    except DetallePedido.DoesNotExist:
        return False, "Ítem no encontrado."


@transaction.atomic
def cancelar_pedido(pedido: Pedido) -> tuple[bool, str]:
    """Cancela un pedido pendiente. Solo opera sobre el propio pedido del usuario."""
    if pedido.estado != Pedido.Estado.PENDIENTE:
        return False, "Solo se pueden cancelar pedidos en estado pendiente."
    pedido.estado = Pedido.Estado.CANCELADO
    pedido.save(update_fields=["estado"])
    return True, f"Pedido #{pedido.pk} cancelado correctamente."
