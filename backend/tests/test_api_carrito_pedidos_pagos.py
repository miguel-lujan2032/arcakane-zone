"""Pruebas del carrito, pedidos y pagos a través de la API REST."""
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from cuentas.models import Usuario
from pagos.models import IntentoPago, Venta
from pedidos.models import DetallePedido, Pedido


pytestmark = pytest.mark.django_db


def _auth(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def _otro_cliente():
    return Usuario.objects.create_user(
        username="otro_cliente",
        password="pass1234!",
        email="otro@test.com",
    )


# ── Carrito ─────────────────────────────────────────────────────────────────

def test_carrito_requiere_autenticacion():
    response = APIClient().get("/api/v1/carrito/")

    assert response.status_code == 401


def test_carrito_vacio_no_crea_pedido(usuario_cliente):
    response = _auth(usuario_cliente).get("/api/v1/carrito/")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] is None
    assert data["detalles"] == []
    assert data["total"] == "0.00"
    assert not Pedido.objects.filter(cliente=usuario_cliente).exists()


def test_agregar_item_al_carrito(usuario_cliente, oferta):
    client = _auth(usuario_cliente)

    response = client.post(
        "/api/v1/carrito/items/",
        {"oferta": oferta.pk, "cantidad": 2},
        format="json",
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["cantidad"] == 2
    assert data["precio_unitario"] == "80000.00"
    assert data["subtotal"] == "160000.00"

    carrito = client.get("/api/v1/carrito/")
    assert carrito.status_code == 200
    assert carrito.json()["data"]["total_items"] == 2
    assert len(carrito.json()["data"]["detalles"]) == 1


def test_agregar_misma_oferta_incrementa_cantidad(usuario_cliente, oferta):
    client = _auth(usuario_cliente)

    client.post(
        "/api/v1/carrito/items/",
        {"oferta": oferta.pk, "cantidad": 1},
        format="json",
    )
    response = client.post(
        "/api/v1/carrito/items/",
        {"oferta": oferta.pk, "cantidad": 2},
        format="json",
    )

    assert response.status_code == 201
    pedido = Pedido.objects.get(cliente=usuario_cliente, estado="pendiente")
    assert pedido.detalles.count() == 1
    assert pedido.detalles.first().cantidad == 3


def test_agregar_sin_stock_devuelve_409(usuario_cliente, oferta_agotada):
    response = _auth(usuario_cliente).post(
        "/api/v1/carrito/items/",
        {"oferta": oferta_agotada.pk, "cantidad": 1},
        format="json",
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflicto"


def test_agregar_oferta_no_publicada_devuelve_409(usuario_cliente, oferta):
    oferta.estado_publicacion_id = "retirado"
    oferta.save(update_fields=["estado_publicacion"])

    response = _auth(usuario_cliente).post(
        "/api/v1/carrito/items/",
        {"oferta": oferta.pk, "cantidad": 1},
        format="json",
    )

    assert response.status_code == 409


def test_agregar_cantidad_invalida_devuelve_400(usuario_cliente, oferta):
    response = _auth(usuario_cliente).post(
        "/api/v1/carrito/items/",
        {"oferta": oferta.pk, "cantidad": 0},
        format="json",
    )

    assert response.status_code == 400
    assert "cantidad" in response.json()["error"]["details"]


def test_agregar_oferta_inexistente_devuelve_400(usuario_cliente):
    response = _auth(usuario_cliente).post(
        "/api/v1/carrito/items/",
        {"oferta": 999999, "cantidad": 1},
        format="json",
    )

    assert response.status_code == 400
    assert "oferta" in response.json()["error"]["details"]


def test_actualizar_cantidad_y_eliminar_item(usuario_cliente, oferta, pedido_con_item):
    detalle = pedido_con_item.detalles.first()
    client = _auth(usuario_cliente)

    actualizado = client.patch(
        f"/api/v1/carrito/items/{detalle.pk}/",
        {"cantidad": 4},
        format="json",
    )
    assert actualizado.status_code == 200
    assert actualizado.json()["data"]["cantidad"] == 4

    eliminado = client.delete(f"/api/v1/carrito/items/{detalle.pk}/")
    assert eliminado.status_code == 200
    assert not DetallePedido.objects.filter(pk=detalle.pk).exists()


def test_actualizar_por_encima_del_stock_devuelve_409(
    usuario_cliente, oferta, pedido_con_item
):
    detalle = pedido_con_item.detalles.first()

    response = _auth(usuario_cliente).patch(
        f"/api/v1/carrito/items/{detalle.pk}/",
        {"cantidad": oferta.stock + 1},
        format="json",
    )

    assert response.status_code == 409


def test_cantidad_cero_elimina_el_item(usuario_cliente, pedido_con_item):
    detalle = pedido_con_item.detalles.first()

    response = _auth(usuario_cliente).patch(
        f"/api/v1/carrito/items/{detalle.pk}/",
        {"cantidad": 0},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["data"] is None
    assert not DetallePedido.objects.filter(pk=detalle.pk).exists()


def test_no_se_puede_modificar_item_de_otro_usuario(usuario_cliente, pedido_con_item):
    detalle = pedido_con_item.detalles.first()

    response = _auth(_otro_cliente()).patch(
        f"/api/v1/carrito/items/{detalle.pk}/",
        {"cantidad": 1},
        format="json",
    )

    assert response.status_code == 404


def test_vaciar_carrito(usuario_cliente, pedido_con_item):
    client = _auth(usuario_cliente)

    response = client.delete("/api/v1/carrito/")

    assert response.status_code == 200
    assert not DetallePedido.objects.filter(pedido=pedido_con_item).exists()


# ── Pedidos ─────────────────────────────────────────────────────────────────

def test_listado_de_pedidos_solo_incluye_los_del_cliente(
    usuario_cliente, usuario_admin, pedido_con_item
):
    otro_pedido = Pedido.objects.create(
        cliente=usuario_admin, estado_id="pagado"
    )
    DetallePedido.objects.create(
        pedido=otro_pedido,
        oferta=pedido_con_item.detalles.first().oferta,
        cantidad=1,
        precio_unitario="1000.00",
    )

    response = _auth(usuario_cliente).get("/api/v1/pedidos/")

    assert response.status_code == 200
    assert response.json()["pagination"]["count"] == 1
    assert response.json()["data"][0]["id"] == pedido_con_item.pk


def test_detalle_de_pedido_ajeno_devuelve_404(usuario_cliente, pedido_con_item):
    response = _auth(_otro_cliente()).get(f"/api/v1/pedidos/{pedido_con_item.pk}/")

    assert response.status_code == 404


def test_admin_puede_ver_pedidos_de_clientes(
    usuario_admin, usuario_cliente, pedido_con_item
):
    response = _auth(usuario_admin).get("/api/v1/pedidos/")

    assert response.status_code == 200
    assert response.json()["pagination"]["count"] == 1


def test_cancelar_pedido_pendiente_con_patch(usuario_cliente, pedido_con_item):
    client = _auth(usuario_cliente)

    response = client.patch(
        f"/api/v1/pedidos/{pedido_con_item.pk}/",
        {"estado": "cancelado"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["data"]["estado"] == "cancelado"
    pedido_con_item.refresh_from_db()
    assert pedido_con_item.estado_id == "cancelado"


def test_cancelar_pedido_pendiente_con_accion(usuario_cliente, pedido_con_item):
    response = _auth(usuario_cliente).post(
        f"/api/v1/pedidos/{pedido_con_item.pk}/cancelar/"
    )

    assert response.status_code == 200
    assert response.json()["data"]["estado"] == "cancelado"


def test_no_cancelar_pedido_pagado(usuario_cliente, pedido_con_item):
    pedido_con_item.estado_id = "pagado"
    pedido_con_item.save(update_fields=["estado"])

    response = _auth(usuario_cliente).patch(
        f"/api/v1/pedidos/{pedido_con_item.pk}/",
        {"estado": "cancelado"},
        format="json",
    )

    assert response.status_code == 409


def test_patch_solo_permite_estado_cancelado(usuario_cliente, pedido_con_item):
    client = _auth(usuario_cliente)

    estado_invalido = client.patch(
        f"/api/v1/pedidos/{pedido_con_item.pk}/",
        {"estado": "pagado"},
        format="json",
    )
    campo_invalido = client.patch(
        f"/api/v1/pedidos/{pedido_con_item.pk}/",
        {"cliente": 1},
        format="json",
    )

    assert estado_invalido.status_code == 400
    assert campo_invalido.status_code == 400


# ── Pagos ───────────────────────────────────────────────────────────────────

def test_pago_aprobado(usuario_cliente, pedido_con_item, oferta):
    stock_inicial = oferta.stock
    cantidad = pedido_con_item.detalles.first().cantidad
    client = _auth(usuario_cliente)

    with patch("pagos.services.random.random", return_value=0.0):
        response = client.post(
            "/api/v1/pagos/",
            {"pedido": pedido_con_item.pk},
            format="json",
        )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["estado"] == "aprobado"
    assert data["pedido"] == pedido_con_item.pk

    pedido_con_item.refresh_from_db()
    oferta.refresh_from_db()
    assert pedido_con_item.estado_id == "pagado"
    assert oferta.stock == stock_inicial - cantidad
    assert Venta.objects.filter(pedido=pedido_con_item).exists()


def test_pago_rechazado_devuelve_402_y_no_cambia_stock(
    usuario_cliente, pedido_con_item, oferta
):
    stock_inicial = oferta.stock

    with patch("pagos.services.random.random", return_value=0.95):
        response = _auth(usuario_cliente).post(
            "/api/v1/pagos/",
            {"pedido": pedido_con_item.pk},
            format="json",
        )

    assert response.status_code == 402
    assert response.json()["error"]["code"] == "pago_rechazado"
    pedido_con_item.refresh_from_db()
    oferta.refresh_from_db()
    assert pedido_con_item.estado_id == "pendiente"
    assert oferta.stock == stock_inicial


def test_reintento_despues_de_rechazo(usuario_cliente, pedido_con_item):
    client = _auth(usuario_cliente)

    with patch("pagos.services.random.random", return_value=0.95):
        rechazado = client.post(
            "/api/v1/pagos/",
            {"pedido": pedido_con_item.pk},
            format="json",
        )
    with patch("pagos.services.random.random", return_value=0.0):
        aprobado = client.post(
            "/api/v1/pagos/",
            {"pedido": pedido_con_item.pk},
            format="json",
        )

    assert rechazado.status_code == 402
    assert aprobado.status_code == 201
    # La normalización conserva los dos intentos; el rechazo no bloqueó el reintento.
    assert IntentoPago.objects.filter(pedido=pedido_con_item).count() == 2
    pedido_con_item.refresh_from_db()
    assert pedido_con_item.estado_id == "pagado"
    assert pedido_con_item.pago.estado_id == "aprobado"


def test_no_pagar_pedido_de_otro_usuario(usuario_cliente, pedido_con_item):
    response = _auth(_otro_cliente()).post(
        "/api/v1/pagos/",
        {"pedido": pedido_con_item.pk},
        format="json",
    )

    assert response.status_code == 404


def test_no_pagar_pedido_ya_pagado(usuario_cliente, pedido_con_item, oferta):
    pedido_con_item.estado_id = "pagado"
    pedido_con_item.save(update_fields=["estado"])

    response = _auth(usuario_cliente).post(
        "/api/v1/pagos/",
        {"pedido": pedido_con_item.pk},
        format="json",
    )

    assert response.status_code == 409


def test_pago_con_pedido_inexistente_devuelve_400(usuario_cliente):
    response = _auth(usuario_cliente).post(
        "/api/v1/pagos/",
        {"pedido": 999999},
        format="json",
    )

    assert response.status_code == 400
    assert "pedido" in response.json()["error"]["details"]


def test_listado_de_pagos_solo_muestra_los_propios(
    usuario_cliente, usuario_admin, pedido_con_item
):
    IntentoPago.objects.create(
        pedido=pedido_con_item,
        importe=pedido_con_item.total,
        estado_id="aprobado",
        referencia="ABC123",
    )
    otro = Pedido.objects.create(
        cliente=usuario_admin, estado_id="pagado"
    )
    IntentoPago.objects.create(
        pedido=otro,
        importe="1000.00",
        estado_id="aprobado",
        referencia="XYZ789",
    )

    response = _auth(usuario_cliente).get("/api/v1/pagos/")

    assert response.status_code == 200
    assert response.json()["pagination"]["count"] == 1
    assert response.json()["data"][0]["referencia"] == "ABC123"
    assert response.json()["data"][0]["monto"] == "160000.00"


def test_pedido_con_varios_intentos_expone_el_aprobado(usuario_cliente, pedido_con_item):
    rechazado = IntentoPago.objects.create(
        pedido=pedido_con_item,
        importe=pedido_con_item.total,
        estado_id="rechazado",
        referencia="REF-RECHAZO",
    )
    aprobado = IntentoPago.objects.create(
        pedido=pedido_con_item,
        importe=pedido_con_item.total,
        estado_id="aprobado",
        referencia="REF-APROBADO",
    )

    data = _auth(usuario_cliente).get(
        f"/api/v1/pedidos/{pedido_con_item.pk}/"
    ).json()["data"]

    assert data["estado"] == "pendiente"
    assert data["pago"]["estado"] == "aprobado"
    assert data["pago"]["referencia"] == aprobado.referencia
    assert data["pago"]["monto"] == "160000.00"
    assert {intento["referencia"] for intento in data["intentos_pago"]} == {
        rechazado.referencia,
        aprobado.referencia,
    }
