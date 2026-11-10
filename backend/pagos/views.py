from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from pedidos.models import Pedido
from pedidos.services import validar_para_checkout

from .services import procesar_pago_simulado


@login_required
def checkout(request, pedido_id):
    pedido = get_object_or_404(
        Pedido, pk=pedido_id, cliente=request.user, estado=Pedido.Estado.PENDIENTE
    )
    errores = validar_para_checkout(pedido)
    if errores:
        for error in errores:
            messages.error(request, error)
        return redirect("pedidos:carrito")

    detalles = pedido.detalles.select_related("oferta__videojuego", "oferta__plataforma").all()
    return render(request, "pagos/checkout.html", {"pedido": pedido, "detalles": detalles})


@login_required
def procesar_pago(request, pedido_id):
    if request.method != "POST":
        return redirect("pagos:checkout", pedido_id=pedido_id)

    pedido = get_object_or_404(
        Pedido, pk=pedido_id, cliente=request.user, estado=Pedido.Estado.PENDIENTE
    )
    # Re-validar stock justo antes de cobrar
    errores = validar_para_checkout(pedido)
    if errores:
        for error in errores:
            messages.error(request, error)
        return redirect("pedidos:carrito")

    exito, mensaje = procesar_pago_simulado(pedido)
    if exito:
        messages.success(request, mensaje)
        return redirect("pedidos:detalle", pk=pedido_id)
    messages.error(request, mensaje)
    return redirect("pagos:checkout", pedido_id=pedido_id)
