"""
Pruebas de cancelación de pedidos:
  - Un pedido pendiente SÍ puede cancelarse
  - Un pedido pagado NO puede cancelarse
  - Un pedido ya cancelado NO puede cancelarse de nuevo
"""
from unittest.mock import patch

import pytest

from pagos.services import procesar_pago_simulado
from pedidos.models import Pedido
from pedidos.services import cancelar_pedido


@pytest.mark.django_db
def test_cancelar_pedido_pendiente(pedido_con_item):
    exito, mensaje = cancelar_pedido(pedido_con_item)

    assert exito is True
    pedido_con_item.refresh_from_db()
    assert pedido_con_item.estado == Pedido.Estado.CANCELADO


@pytest.mark.django_db
def test_no_cancelar_pedido_pagado(pedido_con_item):
    with patch("pagos.services.random.random", return_value=0.0):
        procesar_pago_simulado(pedido_con_item)

    pedido_con_item.refresh_from_db()
    assert pedido_con_item.estado == Pedido.Estado.PAGADO

    exito, mensaje = cancelar_pedido(pedido_con_item)
    assert exito is False
    assert "pendiente" in mensaje.lower()
    pedido_con_item.refresh_from_db()
    assert pedido_con_item.estado == Pedido.Estado.PAGADO  # no cambió


@pytest.mark.django_db
def test_no_cancelar_pedido_ya_cancelado(pedido_con_item):
    cancelar_pedido(pedido_con_item)
    exito, mensaje = cancelar_pedido(pedido_con_item)  # segundo intento
    assert exito is False
    assert "pendiente" in mensaje.lower()
