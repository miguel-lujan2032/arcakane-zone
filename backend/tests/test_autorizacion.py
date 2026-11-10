"""
Pruebas de autorización:
  - Visitante (no autenticado) es redirigido al login
  - Cliente autenticado (no staff) es redirigido al intentar acceder a reportes
  - Administrador (is_staff) puede acceder a los reportes
"""
import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


URLS_REPORTES = [
    "/reportes/dashboard/",
    "/reportes/ventas/",
    "/reportes/inventario/",
    "/reportes/videojuegos/",
]


@pytest.mark.django_db
@pytest.mark.parametrize("url", URLS_REPORTES)
def test_visitante_redirigido_al_login(client, url):
    response = client.get(url)
    assert response.status_code == 302
    assert "/login" in response["Location"] or "login" in response["Location"]


@pytest.mark.django_db
@pytest.mark.parametrize("url", URLS_REPORTES)
def test_cliente_sin_staff_redirigido(client, usuario_cliente, url):
    client.force_login(usuario_cliente)
    response = client.get(url)
    # staff_member_required redirige al login (302) o devuelve 403
    assert response.status_code in (302, 403)


@pytest.mark.django_db
@pytest.mark.parametrize("url", URLS_REPORTES)
def test_admin_con_staff_puede_acceder(client, usuario_admin, url):
    client.force_login(usuario_admin)
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_cliente_puede_acceder_a_su_perfil(client, usuario_cliente):
    client.force_login(usuario_cliente)
    response = client.get("/cuentas/perfil/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_visitante_no_puede_acceder_a_perfil(client):
    response = client.get("/cuentas/perfil/")
    assert response.status_code == 302
    assert "login" in response["Location"]
