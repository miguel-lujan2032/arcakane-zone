from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from .models import DetallePedido, Pedido
from .services import (
    actualizar_cantidad,
    agregar_o_incrementar,
    cancelar_pedido,
    get_or_create_carrito,
    quitar_item,
)


def _es_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _render_carrito_zona(request, mensaje="", exito=True):
    pedido = get_or_create_carrito(request.user)
    detalles = pedido.detalles.select_related(
        "oferta__videojuego", "oferta__plataforma"
    ).all()
    return render(request, "pedidos/_carrito_contenido.html", {
        "pedido": pedido,
        "detalles": detalles,
        "mensaje": mensaje,
        "exito": exito,
    })


# ── Carrito ────────────────────────────────────────────────────────────────

@login_required
def carrito(request):
    pedido = get_or_create_carrito(request.user)
    detalles = pedido.detalles.select_related(
        "oferta__videojuego", "oferta__plataforma"
    ).all()
    return render(request, "pedidos/carrito.html", {"pedido": pedido, "detalles": detalles})


@login_required
def agregar_al_carrito(request, oferta_id):
    if request.method != "POST":
        return redirect("catalogo:lista")

    exito, mensaje = agregar_o_incrementar(request.user, oferta_id)

    if _es_htmx(request):
        hx_target = request.headers.get("HX-Target", "")
        if hx_target == "toast-carrito":
            return render(request, "pedidos/_toast.html", {"mensaje": mensaje, "exito": exito})
        if hx_target == "toast-detalle":
            pedido = get_or_create_carrito(request.user) if exito else None
            return render(request, "pedidos/_detalle_toast.html", {
                "mensaje": mensaje,
                "exito": exito,
                "pedido": pedido,
            })
        return _render_carrito_zona(request, mensaje, exito)

    if exito:
        messages.success(request, mensaje)
    else:
        messages.error(request, mensaje)
    return redirect("pedidos:carrito")


@login_required
def actualizar_item(request, detalle_id):
    if request.method != "POST":
        return redirect("pedidos:carrito")

    cantidad = int(request.POST.get("cantidad", 1))
    exito, mensaje = actualizar_cantidad(request.user, detalle_id, cantidad)

    if _es_htmx(request):
        return _render_carrito_zona(request, mensaje, exito)

    if exito:
        messages.success(request, mensaje)
    else:
        messages.error(request, mensaje)
    return redirect("pedidos:carrito")


@login_required
def quitar_del_carrito(request, detalle_id):
    if request.method != "POST":
        return redirect("pedidos:carrito")

    exito, mensaje = quitar_item(request.user, detalle_id)

    if _es_htmx(request):
        return _render_carrito_zona(request, mensaje, exito)

    if exito:
        messages.success(request, mensaje)
    else:
        messages.error(request, mensaje)
    return redirect("pedidos:carrito")


# ── Pedidos ────────────────────────────────────────────────────────────────

@login_required
def mis_pedidos(request):
    """
    HU17/HU18: muestra TODOS los pedidos del cliente (todos los estados).
    El pedido activo en carrito aparece como 'Pendiente'.
    """
    pedidos = (
        Pedido.objects.filter(cliente=request.user)
        .annotate(num_detalles=Count("detalles"))
        .exclude(num_detalles=0)
        .prefetch_related("detalles")
        .order_by("-creado_en")
    )
    return render(request, "pedidos/mis_pedidos.html", {"pedidos": pedidos})


@login_required
def detalle_pedido(request, pk):
    """HU18: detalle completo de un pedido del cliente."""
    pedido = get_object_or_404(Pedido, pk=pk, cliente=request.user)
    detalles = pedido.detalles.all()
    return render(request, "pedidos/detalle.html", {"pedido": pedido, "detalles": detalles})


@login_required
def cancelar_pedido_view(request, pk):
    """HU19: cancela un pedido pendiente del cliente."""
    if request.method != "POST":
        return redirect("pedidos:mis_pedidos")

    pedido = get_object_or_404(Pedido, pk=pk, cliente=request.user)
    exito, mensaje = cancelar_pedido(pedido)

    if exito:
        messages.success(request, mensaje)
    else:
        messages.error(request, mensaje)
    return redirect("pedidos:mis_pedidos")
