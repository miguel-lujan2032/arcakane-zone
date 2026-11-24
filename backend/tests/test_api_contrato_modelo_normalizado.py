"""Contrato JSON aditivo tras la normalización del modelo (AZ-S2-BE-02)."""
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from catalogo.models import (
    Categoria,
    Genero,
    VideojuegoCategoria,
    VideojuegoGenero,
)


pytestmark = pytest.mark.django_db


def _auth(usuario):
    client = APIClient()
    client.force_authenticate(usuario)
    return client


def test_estados_del_contrato_conservan_sus_textos(usuario_cliente, pedido_con_item):
    client = _auth(usuario_cliente)

    pendiente = client.get("/api/v1/pedidos/").json()["data"][0]
    assert pendiente["estado"] == "pendiente"

    with patch("pagos.services.random.random", return_value=0.95):
        rechazado = client.post(
            "/api/v1/pagos/", {"pedido": pedido_con_item.pk}, format="json"
        )
    with patch("pagos.services.random.random", return_value=0.0):
        aprobado = client.post(
            "/api/v1/pagos/", {"pedido": pedido_con_item.pk}, format="json"
        )

    assert rechazado.status_code == 402
    assert rechazado.json()["error"]["details"]["estado"] == "rechazado"
    assert aprobado.status_code == 201
    assert aprobado.json()["data"]["estado"] == "aprobado"

    pagado = client.get(f"/api/v1/pedidos/{pedido_con_item.pk}/").json()["data"]
    assert pagado["estado"] == "pagado"
    assert pagado["pago"]["estado"] == "aprobado"


def test_reporte_videojuegos_no_duplica_por_categorias_multiples(
    usuario_admin, videojuego, oferta, categoria, genero
):
    VideojuegoCategoria.objects.create(
        videojuego=videojuego, categoria=Categoria.objects.create(nombre="Zona")
    )
    VideojuegoGenero.objects.create(
        videojuego=videojuego, genero=Genero.objects.create(nombre="Zelda")
    )

    response = _auth(usuario_admin).get(
        "/api/v1/reportes/videojuegos/", {"categoria": categoria.pk}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["count"] == 1
    assert [o["id"] for o in payload["data"]["resultados"]] == [oferta.pk]


def test_perfil_expone_roles_aditivos_y_campo_historico(
    usuario_cliente, rol_cliente, rol_admin
):
    usuario_cliente.roles.add(rol_admin)

    data = _auth(usuario_cliente).get("/api/v1/auth/me/").json()["data"]

    assert data["rol"] == rol_admin.pk
    assert data["rol_nombre"] == "administrador"
    assert set(data["roles"]) == {rol_cliente.pk, rol_admin.pk}
