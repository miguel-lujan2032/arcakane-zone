"""Pruebas de los endpoints JSON de la API."""
from unittest.mock import patch

import pytest

from pagos.models import Pago, Venta
from pagos.services import procesar_pago_simulado
from pedidos.models import Pedido
from soporte.models import Contacto


# ── Salud y autenticación ────────────────────────────────────────────────────

def test_health(api_client):
    response = api_client.get("/api/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_registro_devuelve_token_y_usuario(api_client):
    payload = {
        "username": "nuevo_cliente",
        "email": "nuevo@test.com",
        "first_name": "Nuevo",
        "last_name": "Cliente",
        "password": "ClaveSegura123!",
        "password_confirm": "ClaveSegura123!",
    }
    response = api_client.post("/api/v1/auth/register/", payload, format="json")

    assert response.status_code == 201
    assert response.data["token"]
    assert response.data["user"]["username"] == "nuevo_cliente"
    assert response.data["user"]["rol"]["nombre"] == "cliente"


@pytest.mark.django_db
def test_registro_rechaza_password_distinta(api_client):
    payload = {
        "username": "otro_cliente",
        "email": "otro@test.com",
        "password": "ClaveSegura123!",
        "password_confirm": "OtraClave123!",
    }
    response = api_client.post("/api/v1/auth/register/", payload, format="json")
    assert response.status_code == 400
    assert "password_confirm" in response.data


@pytest.mark.django_db
def test_login_devuelve_token(api_client, usuario_cliente):
    response = api_client.post(
        "/api/v1/auth/login/",
        {"username": "cliente_test", "password": "pass1234!"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["token"]


@pytest.mark.django_db
def test_login_rechaza_credenciales_invalidas(api_client, usuario_cliente):
    response = api_client.post(
        "/api/v1/auth/login/",
        {"username": "cliente_test", "password": "incorrecta"},
        format="json",
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_cambio_de_password(api_cliente, usuario_cliente):
    response = api_cliente.post(
        "/api/v1/auth/change-password/",
        {
            "old_password": "pass1234!",
            "new_password": "NuevaClave456!",
            "new_password_confirm": "NuevaClave456!",
        },
        format="json",
    )
    assert response.status_code == 200
    usuario_cliente.refresh_from_db()
    assert usuario_cliente.check_password("NuevaClave456!")


@pytest.mark.django_db
def test_logout_invalida_el_token(api_cliente):
    response = api_cliente.post("/api/v1/auth/logout/")
    assert response.status_code == 204

    response = api_cliente.get("/api/v1/auth/me/")
    assert response.status_code == 401


# ── Catálogo ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_catalogo_lista_paginada(api_client, videojuego):
    response = api_client.get("/api/v1/catalogo/videojuegos/")
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["titulo"] == videojuego.titulo


@pytest.mark.django_db
def test_catalogo_filtra_por_categoria_y_busqueda(api_client, videojuego):
    response = api_client.get(
        "/api/v1/catalogo/videojuegos/",
        {"categoria": videojuego.categoria_id, "q": "alpha"},
    )
    assert response.status_code == 200
    assert response.data["count"] == 1


@pytest.mark.django_db
def test_catalogo_no_muestra_inactivos_al_publico(api_client, videojuego):
    videojuego.activo = False
    videojuego.save(update_fields=["activo"])

    response = api_client.get("/api/v1/catalogo/videojuegos/")
    assert response.data["count"] == 0


@pytest.mark.django_db
def test_catalogo_rechaza_filtros_invalidos(api_client):
    response = api_client.get(
        "/api/v1/catalogo/videojuegos/", {"categoria": "abc"}
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_catalogo_rechaza_disponibilidad_invalida(api_client):
    response = api_client.get(
        "/api/v1/catalogo/videojuegos/", {"disponible": "tal-vez"}
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_catalogo_rechaza_precio_invalido(api_client):
    response = api_client.get(
        "/api/v1/catalogo/videojuegos/", {"precio_min": "abc"}
    )
    assert response.status_code == 400


# ── Carrito ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_agregar_item_al_carrito(api_cliente, videojuego):
    response = api_cliente.post(
        "/api/v1/pedidos/carrito/items/",
        {"videojuego_id": videojuego.pk, "cantidad": 2},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["pedido"]["detalles"][0]["cantidad"] == 2
    assert response.data["pedido"]["total"] == "160000.00"


@pytest.mark.django_db
def test_agregar_item_respeta_stock(api_cliente, videojuego):
    response = api_cliente.post(
        "/api/v1/pedidos/carrito/items/",
        {"videojuego_id": videojuego.pk, "cantidad": videojuego.stock + 1},
        format="json",
    )
    assert response.status_code == 400
    assert "stock" in response.data["detail"].lower()


@pytest.mark.django_db
def test_actualizar_y_eliminar_item(api_cliente, videojuego):
    agregado = api_cliente.post(
        "/api/v1/pedidos/carrito/items/",
        {"videojuego_id": videojuego.pk, "cantidad": 2},
        format="json",
    )
    detalle_id = agregado.data["pedido"]["detalles"][0]["id"]

    actualizado = api_cliente.patch(
        f"/api/v1/pedidos/carrito/items/{detalle_id}/",
        {"cantidad": 1},
        format="json",
    )
    assert actualizado.status_code == 200
    assert actualizado.data["pedido"]["detalles"][0]["cantidad"] == 1

    eliminado = api_cliente.delete(
        f"/api/v1/pedidos/carrito/items/{detalle_id}/"
    )
    assert eliminado.status_code == 200
    assert eliminado.data["pedido"]["detalles"] == []


@pytest.mark.django_db
def test_cliente_puede_modificar_su_propio_item(api_cliente, pedido_con_item):
    detalle = pedido_con_item.detalles.first()
    response = api_cliente.patch(
        f"/api/v1/pedidos/carrito/items/{detalle.pk}/",
        {"cantidad": 1},
        format="json",
    )
    assert response.status_code == 200


# ── Pedidos ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_historial_de_pedidos(api_cliente, pedido_con_item):
    response = api_cliente.get("/api/v1/pedidos/")
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["id"] == pedido_con_item.pk


@pytest.mark.django_db
def test_detalle_de_pedido(api_cliente, pedido_con_item):
    response = api_cliente.get(f"/api/v1/pedidos/{pedido_con_item.pk}/")
    assert response.status_code == 200
    assert response.data["detalles"][0]["videojuego"]["titulo"] == "Juego Alpha"


@pytest.mark.django_db
def test_cancelar_pedido(api_cliente, pedido_con_item):
    response = api_cliente.post(
        f"/api/v1/pedidos/{pedido_con_item.pk}/cancelar/"
    )
    assert response.status_code == 200
    assert response.data["pedido"]["estado"] == Pedido.Estado.CANCELADO


@pytest.mark.django_db
def test_no_cancelar_pedido_pagado(api_cliente, pedido_con_item):
    with patch("pagos.services.random.random", return_value=0.0):
        procesar_pago_simulado(pedido_con_item)

    response = api_cliente.post(
        f"/api/v1/pedidos/{pedido_con_item.pk}/cancelar/"
    )
    assert response.status_code == 400


# ── Pagos ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_checkout_valida_el_pedido(api_cliente, pedido_con_item):
    response = api_cliente.get(
        f"/api/v1/pagos/checkout/{pedido_con_item.pk}/"
    )
    assert response.status_code == 200
    assert response.data["valido"] is True
    assert response.data["errores"] == []


@pytest.mark.django_db
def test_pago_aprobado(api_cliente, pedido_con_item, videojuego):
    stock_inicial = videojuego.stock
    cantidad = pedido_con_item.detalles.first().cantidad

    with patch("pagos.services.random.random", return_value=0.0):
        response = api_cliente.post(
            f"/api/v1/pagos/procesar/{pedido_con_item.pk}/"
        )

    assert response.status_code == 200
    assert response.data["aprobado"] is True
    assert response.data["pedido"]["estado"] == Pedido.Estado.PAGADO

    videojuego.refresh_from_db()
    assert videojuego.stock == stock_inicial - cantidad
    assert Venta.objects.filter(pedido=pedido_con_item).exists()


@pytest.mark.django_db
def test_reintento_de_pago_rechazado_no_duplica_el_pago(
    api_cliente, pedido_con_item
):
    with patch("pagos.services.random.random", return_value=0.95):
        rechazado = api_cliente.post(
            f"/api/v1/pagos/procesar/{pedido_con_item.pk}/"
        )
    assert rechazado.status_code == 200
    assert rechazado.data["aprobado"] is False

    with patch("pagos.services.random.random", return_value=0.0):
        aprobado = api_cliente.post(
            f"/api/v1/pagos/procesar/{pedido_con_item.pk}/"
        )
    assert aprobado.status_code == 200
    assert aprobado.data["aprobado"] is True

    assert Pago.objects.filter(pedido=pedido_con_item).count() == 1


# ── Soporte ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_contacto_publico(api_client):
    response = api_client.post(
        "/api/v1/soporte/contacto/",
        {
            "nombre": "Visitante",
            "email": "visitante@test.com",
            "telefono": "3001234567",
            "asunto": "Consulta",
            "mensaje": "Hola",
        },
        format="json",
    )
    assert response.status_code == 201
    assert Contacto.objects.count() == 1


@pytest.mark.django_db
def test_mayor_informacion_publico(api_client):
    response = api_client.post(
        "/api/v1/soporte/mayor-informacion/",
        {
            "nombre": "Interesado",
            "email": "interesado@test.com",
            "telefono": "3007654321",
        },
        format="json",
    )
    assert response.status_code == 201
    assert Contacto.objects.get().asunto == "Solicitud de información"


@pytest.mark.django_db
def test_contacto_autenticado_completa_nombre_y_email(
    api_cliente, usuario_cliente
):
    response = api_cliente.post(
        "/api/v1/soporte/contacto/",
        {"asunto": "Consulta", "mensaje": "Hola"},
        format="json",
    )
    assert response.status_code == 201

    contacto = Contacto.objects.get()
    assert contacto.usuario == usuario_cliente
    assert contacto.nombre == usuario_cliente.username
    assert contacto.email == usuario_cliente.email


@pytest.mark.django_db
def test_staff_puede_marcar_contacto_atendido(api_admin):
    contacto = Contacto.objects.create(
        nombre="Cliente",
        email="cliente@test.com",
        asunto="Ayuda",
        mensaje="Necesito ayuda",
    )

    listado = api_admin.get("/api/v1/soporte/contactos/")
    assert listado.status_code == 200
    assert listado.data["count"] == 1

    response = api_admin.patch(
        f"/api/v1/soporte/contactos/{contacto.pk}/",
        {"atendido": True},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["atendido"] is True
    assert response.data["nombre"] == "Cliente"
    assert response.data["email"] == "cliente@test.com"


@pytest.mark.django_db
def test_cliente_no_puede_listar_contactos(api_cliente):
    response = api_cliente.get("/api/v1/soporte/contactos/")
    assert response.status_code == 403


# ── Reportes ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_dashboard_refleja_ventas(api_admin, pedido_con_item):
    with patch("pagos.services.random.random", return_value=0.0):
        procesar_pago_simulado(pedido_con_item)

    response = api_admin.get("/api/v1/reportes/dashboard/")
    assert response.status_code == 200
    assert response.data["pedidos_por_estado"]["pagado"] == 1
    assert float(response.data["total_ventas"]) == float(pedido_con_item.total)


@pytest.mark.django_db
def test_reporte_ventas_lista_ventas(api_admin, pedido_con_item):
    with patch("pagos.services.random.random", return_value=0.0):
        procesar_pago_simulado(pedido_con_item)

    response = api_admin.get("/api/v1/reportes/ventas/")
    assert response.status_code == 200
    assert response.data["num_ventas"] == 1
    assert response.data["ventas"][0]["detalles"][0]["videojuego"] == "Juego Alpha"


@pytest.mark.django_db
def test_reporte_ventas_rechaza_fechas_invalidas(api_admin):
    response = api_admin.get(
        "/api/v1/reportes/ventas/", {"desde": "2026-99-99"}
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_reporte_inventario_rechaza_filtro_invalido(api_admin):
    response = api_admin.get(
        "/api/v1/reportes/inventario/", {"filtro": "inventado"}
    )
    assert response.status_code == 400


@pytest.mark.django_db
def test_reporte_videojuegos_filtra_por_categoria(api_admin, videojuego):
    response = api_admin.get(
        "/api/v1/reportes/videojuegos/",
        {"categoria": videojuego.categoria_id},
    )
    assert response.status_code == 200
    assert len(response.data["videojuegos"]) == 1


@pytest.mark.django_db
def test_reporte_videojuegos_rechaza_estado_invalido(api_admin):
    response = api_admin.get(
        "/api/v1/reportes/videojuegos/", {"estado": "desconocido"}
    )
    assert response.status_code == 400
