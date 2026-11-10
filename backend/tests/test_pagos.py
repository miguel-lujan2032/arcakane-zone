"""
Pruebas del pago simulado:
  - Aprobado: estado → pagado, stock descontado, Venta generada
  - Rechazado: estado sigue pendiente, stock sin cambios, Venta NO generada
  - No se puede pagar un pedido ya pagado
"""
from unittest.mock import patch

import pytest

from pagos.models import Pago, Venta
from pagos.services import procesar_pago_simulado
from pedidos.models import Pedido


@pytest.mark.django_db
def test_pago_aprobado_cambia_estado_a_pagado(pedido_con_item):
    with patch("pagos.services.random.random", return_value=0.0):  # 0.0 < 0.9 → aprobado
        exito, _ = procesar_pago_simulado(pedido_con_item)

    assert exito is True
    pedido_con_item.refresh_from_db()
    assert pedido_con_item.estado == Pedido.Estado.PAGADO


@pytest.mark.django_db
def test_pago_aprobado_descuenta_stock(pedido_con_item, oferta):
    stock_inicial = oferta.stock
    cantidad_pedida = pedido_con_item.detalles.first().cantidad

    with patch("pagos.services.random.random", return_value=0.0):
        procesar_pago_simulado(pedido_con_item)

    oferta.refresh_from_db()
    assert oferta.stock == stock_inicial - cantidad_pedida


@pytest.mark.django_db
def test_pago_aprobado_genera_venta(pedido_con_item):
    with patch("pagos.services.random.random", return_value=0.0):
        procesar_pago_simulado(pedido_con_item)

    assert Venta.objects.filter(pedido=pedido_con_item).exists()
    venta = Venta.objects.get(pedido=pedido_con_item)
    assert venta.total == pedido_con_item.total


@pytest.mark.django_db
def test_pago_rechazado_no_cambia_estado(pedido_con_item):
    with patch("pagos.services.random.random", return_value=0.95):  # 0.95 >= 0.9 → rechazado
        exito, _ = procesar_pago_simulado(pedido_con_item)

    assert exito is False
    pedido_con_item.refresh_from_db()
    assert pedido_con_item.estado == Pedido.Estado.PENDIENTE


@pytest.mark.django_db
def test_pago_rechazado_no_descuenta_stock(pedido_con_item, oferta):
    stock_inicial = oferta.stock

    with patch("pagos.services.random.random", return_value=0.95):
        procesar_pago_simulado(pedido_con_item)

    oferta.refresh_from_db()
    assert oferta.stock == stock_inicial


@pytest.mark.django_db
def test_pago_rechazado_no_genera_venta(pedido_con_item):
    with patch("pagos.services.random.random", return_value=0.95):
        procesar_pago_simulado(pedido_con_item)

    assert not Venta.objects.filter(pedido=pedido_con_item).exists()


@pytest.mark.django_db
def test_no_se_puede_pagar_pedido_ya_pagado(pedido_con_item):
    """Intentar pagar un pedido que ya fue pagado debe fallar."""
    with patch("pagos.services.random.random", return_value=0.0):
        procesar_pago_simulado(pedido_con_item)

    # Segundo intento sobre el mismo pedido
    exito, mensaje = procesar_pago_simulado(pedido_con_item)
    assert exito is False
    assert "pendiente" in mensaje.lower()
