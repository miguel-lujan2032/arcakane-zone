"""Pruebas de reportes administrativos y soporte."""
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from pagos.models import Venta
from soporte.models import Contacto

pytestmark = pytest.mark.django_db


def _auth(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


# ── Reportes ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/reportes/dashboard/",
        "/api/v1/reportes/ventas/",
        "/api/v1/reportes/inventario/",
        "/api/v1/reportes/videojuegos/",
    ],
)
def test_reportes_requieren_autenticacion(url):
    assert APIClient().get(url).status_code == 401


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/reportes/dashboard/",
        "/api/v1/reportes/ventas/",
        "/api/v1/reportes/inventario/",
        "/api/v1/reportes/videojuegos/",
    ],
)
def test_reportes_rechazan_clientes(usuario_cliente, url):
    response = _auth(usuario_cliente).get(url)

    assert response.status_code == 403


def test_dashboard_resume_ventas_pedidos_y_stock(
    usuario_admin, pedido_con_item, oferta_agotada, intento_aprobado
):
    Venta.objects.create(
        pedido=pedido_con_item,
        intento_aprobado=intento_aprobado,
        total=Decimal("160000"),
    )
    pedido_con_item.estado_id = "pagado"
    pedido_con_item.save(update_fields=["estado"])

    response = _auth(usuario_admin).get("/api/v1/reportes/dashboard/")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["resumen"]["total_ventas"] == "160000.00"
    assert data["resumen"]["num_pedidos_pagados"] == 1
    assert data["resumen"]["conteo_pagado"] == 1
    assert len(data["agotados"]) == 1


def test_reporte_ventas_valida_fechas(usuario_admin):
    client = _auth(usuario_admin)

    invalida = client.get("/api/v1/reportes/ventas/?desde=no-es-fecha")
    rango_invalido = client.get(
        "/api/v1/reportes/ventas/?desde=2026-02-01&hasta=2026-01-01"
    )

    assert invalida.status_code == 400
    assert rango_invalido.status_code == 400


def test_reporte_ventas_devuelve_resumen_y_resultados(
    usuario_admin, pedido_con_item, intento_aprobado
):
    Venta.objects.create(
        pedido=pedido_con_item,
        intento_aprobado=intento_aprobado,
        total=Decimal("160000"),
    )

    response = _auth(usuario_admin).get("/api/v1/reportes/ventas/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["resumen"]["total_periodo"] == "160000.00"
    assert payload["data"]["resumen"]["cantidad_ventas"] == 1
    assert len(payload["data"]["resultados"]) == 1
    assert payload["pagination"]["count"] == 1


def test_reporte_inventario_filtra_por_estado(usuario_admin, oferta, oferta_agotada):
    client = _auth(usuario_admin)

    invalido = client.get("/api/v1/reportes/inventario/?filtro=inventado")
    agotados = client.get("/api/v1/reportes/inventario/?filtro=agotados")

    assert invalido.status_code == 400
    assert agotados.status_code == 200
    data = agotados.json()["data"]
    assert data["resumen"]["filtro"] == "agotados"
    assert data["resumen"]["total_agotados"] == 1
    assert [o["id"] for o in data["resultados"]] == [oferta_agotada.pk]


def test_reporte_videojuegos_valida_filtros(usuario_admin, oferta):
    client = _auth(usuario_admin)

    invalido = client.get("/api/v1/reportes/videojuegos/?estado=inventado")
    valido = client.get("/api/v1/reportes/videojuegos/?estado=activo&disponibilidad=disponible")

    assert invalido.status_code == 400
    assert valido.status_code == 200
    data = valido.json()["data"]
    assert data["resumen"]["filtros"]["estado"] == "activo"
    assert len(data["resultados"]) == 1


# ── Soporte ─────────────────────────────────────────────────────────────────

def test_contacto_publico_se_puede_crear():
    response = APIClient().post(
        "/api/v1/soporte/contactos/",
        {
            "nombre": "Visitante",
            "email": "visitante@test.com",
            "asunto": "Consulta",
            "mensaje": "Necesito información.",
        },
        format="json",
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["nombre"] == "Visitante"
    assert data["usuario"] is None
    assert Contacto.objects.filter(email="visitante@test.com").exists()


def test_contacto_publico_valida_campos_obligatorios():
    response = APIClient().post(
        "/api/v1/soporte/contactos/",
        {"nombre": "Visitante"},
        format="json",
    )

    assert response.status_code == 400
    detalles = response.json()["error"]["details"]
    assert "email" in detalles
    assert "asunto" in detalles


def test_contacto_de_usuario_autenticado_completa_datos(usuario_cliente):
    response = _auth(usuario_cliente).post(
        "/api/v1/soporte/contactos/",
        {"asunto": "Problema con mi pedido", "mensaje": "Ayuda por favor."},
        format="json",
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["usuario"] == usuario_cliente.pk
    assert data["nombre"] == usuario_cliente.username
    assert data["email"] == usuario_cliente.email


def test_listado_de_contactos_requiere_autenticacion():
    assert APIClient().get("/api/v1/soporte/contactos/").status_code == 401


def test_cliente_solo_ve_sus_contactos(usuario_cliente, usuario_admin):
    propio = Contacto.objects.create(
        nombre="Propio",
        email="propio@test.com",
        asunto="Mío",
        usuario=usuario_cliente,
    )
    Contacto.objects.create(
        nombre="Ajeno",
        email="ajeno@test.com",
        asunto="Ajeno",
        usuario=usuario_admin,
    )

    response = _auth(usuario_cliente).get("/api/v1/soporte/contactos/")

    assert response.status_code == 200
    assert response.json()["pagination"]["count"] == 1
    assert response.json()["data"][0]["id"] == propio.pk


def test_admin_puede_marcar_contacto_atendido(usuario_admin):
    contacto = Contacto.objects.create(
        nombre="Cliente",
        email="cliente@test.com",
        asunto="Consulta",
    )

    response = _auth(usuario_admin).patch(
        f"/api/v1/soporte/contactos/{contacto.pk}/",
        {"atendido": True},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["data"]["atendido"] is True
    contacto.refresh_from_db()
    assert contacto.atendido is True


def test_cliente_no_puede_modificar_contacto(usuario_cliente):
    contacto = Contacto.objects.create(
        nombre="Cliente",
        email="cliente@test.com",
        asunto="Consulta",
        usuario=usuario_cliente,
    )

    response = _auth(usuario_cliente).patch(
        f"/api/v1/soporte/contactos/{contacto.pk}/",
        {"atendido": True},
        format="json",
    )

    assert response.status_code == 403


def test_solicitud_de_mayor_informacion_es_publica():
    response = APIClient().post(
        "/api/v1/soporte/mayor-informacion/",
        {
            "nombre": "Interesado",
            "email": "interesado@test.com",
            "telefono": "3000000000",
        },
        format="json",
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["asunto"] == "Solicitud de información"
    assert data["mensaje"] == ""


def test_solicitud_de_mayor_informacion_valida_correo():
    response = APIClient().post(
        "/api/v1/soporte/mayor-informacion/",
        {"nombre": "Interesado", "email": "no-es-correo"},
        format="json",
    )

    assert response.status_code == 400
    assert "email" in response.json()["error"]["details"]
