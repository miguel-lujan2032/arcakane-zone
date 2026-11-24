"""Pruebas de los recursos administrativos de usuarios, roles y ventas."""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from pagos.models import Venta

pytestmark = pytest.mark.django_db


def _auth(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


# ── Usuarios ────────────────────────────────────────────────────────────────

def test_usuarios_requieren_autenticacion():
    assert APIClient().get("/api/v1/usuarios/").status_code == 401


def test_usuarios_rechazan_clientes(usuario_cliente):
    response = _auth(usuario_cliente).get("/api/v1/usuarios/")

    assert response.status_code == 403


def test_admin_lista_y_filtra_usuarios(usuario_admin, usuario_cliente, rol_cliente):
    client = _auth(usuario_admin)

    listado = client.get("/api/v1/usuarios/")
    busqueda = client.get("/api/v1/usuarios/?q=cliente_test")
    por_rol = client.get(f"/api/v1/usuarios/?rol={rol_cliente.pk}")

    assert listado.status_code == 200
    assert listado.json()["pagination"]["count"] == 2
    assert [u["username"] for u in busqueda.json()["data"]] == ["cliente_test"]
    assert {u["username"] for u in por_rol.json()["data"]} == {"cliente_test"}


def test_admin_obtiene_detalle_de_usuario(usuario_admin, usuario_cliente, rol_cliente):
    response = _auth(usuario_admin).get(f"/api/v1/usuarios/{usuario_cliente.pk}/")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "cliente_test"
    assert data["rol_nombre"] == "cliente"
    assert data["roles"] == [rol_cliente.pk]


def test_usuario_con_varios_roles_expone_el_primero_por_nombre(
    usuario_admin, usuario_cliente, rol_cliente, rol_admin
):
    usuario_cliente.roles.add(rol_admin)

    data = _auth(usuario_admin).get(
        f"/api/v1/usuarios/{usuario_cliente.pk}/"
    ).json()["data"]

    # "administrador" precede a "cliente" al ordenar por nombre.
    assert data["rol"] == rol_admin.pk
    assert data["rol_nombre"] == "administrador"
    assert set(data["roles"]) == {rol_cliente.pk, rol_admin.pk}


# ── Roles ───────────────────────────────────────────────────────────────────

def test_roles_solo_para_administradores(usuario_cliente, usuario_admin):
    cliente = _auth(usuario_cliente).get("/api/v1/roles/")
    admin = _auth(usuario_admin).get("/api/v1/roles/")

    assert cliente.status_code == 403
    assert admin.status_code == 200
    assert {r["nombre"] for r in admin.json()["data"]} == {
        "cliente",
        "administrador",
    }


# ── Ventas ──────────────────────────────────────────────────────────────────

def test_ventas_solo_para_administradores(usuario_cliente, usuario_admin):
    assert _auth(usuario_cliente).get("/api/v1/ventas/").status_code == 403
    assert _auth(usuario_admin).get("/api/v1/ventas/").status_code == 200


def test_admin_lista_ventas_con_filtro_de_cliente(
    usuario_admin, usuario_cliente, pedido_con_item, intento_aprobado
):
    pedido_con_item.estado_id = "pagado"
    pedido_con_item.save(update_fields=["estado"])
    venta = Venta.objects.create(
        pedido=pedido_con_item,
        intento_aprobado=intento_aprobado,
        total=Decimal("160000"),
    )

    client = _auth(usuario_admin)
    listado = client.get("/api/v1/ventas/")
    filtrado = client.get(f"/api/v1/ventas/?cliente={usuario_cliente.pk}")
    detalle = client.get(f"/api/v1/ventas/{venta.pk}/")

    assert listado.status_code == 200
    assert listado.json()["pagination"]["count"] == 1
    assert filtrado.json()["data"][0]["id"] == venta.pk
    assert detalle.json()["data"]["cliente"] == "cliente_test"
    assert detalle.json()["data"]["detalles"][0]["cantidad"] == 2
