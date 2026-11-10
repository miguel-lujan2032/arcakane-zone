"""
Pruebas de las reglas de negocio del carrito:
  - No agregar con stock 0
  - No superar el stock disponible
  - Agregar la misma oferta dos veces incrementa la cantidad (no duplica línea)
"""
import pytest

from pedidos.models import DetallePedido, Pedido
from pedidos.services import agregar_o_incrementar


@pytest.mark.django_db
def test_no_agregar_oferta_agotada(usuario_cliente, oferta_agotada):
    """No se puede agregar al carrito una oferta con stock 0."""
    exito, mensaje = agregar_o_incrementar(usuario_cliente, oferta_agotada.pk)
    assert exito is False
    assert "stock" in mensaje.lower()


@pytest.mark.django_db
def test_no_superar_stock_disponible(usuario_cliente, oferta):
    """No se puede pedir más unidades de las que hay en stock."""
    cantidad_excesiva = oferta.stock + 1
    exito, mensaje = agregar_o_incrementar(usuario_cliente, oferta.pk, cantidad=cantidad_excesiva)
    assert exito is False
    assert "stock" in mensaje.lower() or "insuficiente" in mensaje.lower()


@pytest.mark.django_db
def test_agregar_misma_oferta_incrementa_cantidad(usuario_cliente, oferta):
    """
    Agregar la misma oferta dos veces NO crea dos líneas:
    incrementa la cantidad en la misma DetallePedido.
    """
    agregar_o_incrementar(usuario_cliente, oferta.pk, cantidad=1)
    agregar_o_incrementar(usuario_cliente, oferta.pk, cantidad=2)

    pedido = Pedido.objects.get(cliente=usuario_cliente, estado=Pedido.Estado.PENDIENTE)
    detalles = DetallePedido.objects.filter(pedido=pedido, oferta=oferta)

    assert detalles.count() == 1, "No debe haber más de una línea para la misma oferta"
    assert detalles.first().cantidad == 3


@pytest.mark.django_db
def test_agregar_oferta_hasta_limite_de_stock(usuario_cliente, oferta):
    """Se puede agregar exactamente el stock disponible (caso límite)."""
    exito, _ = agregar_o_incrementar(usuario_cliente, oferta.pk, cantidad=oferta.stock)
    assert exito is True


@pytest.mark.django_db
def test_agregar_crea_carrito_pendiente(usuario_cliente, oferta):
    """Agregar un ítem crea o reutiliza un único pedido en estado pendiente."""
    agregar_o_incrementar(usuario_cliente, oferta.pk, cantidad=1)
    pedidos = Pedido.objects.filter(cliente=usuario_cliente, estado=Pedido.Estado.PENDIENTE)
    assert pedidos.count() == 1
