"""
Pruebas de autorización de la API:
  - Las rutas de reportes requieren staff.
  - Las rutas de carrito y perfil requieren autenticación.
  - El catálogo es de lectura pública y escritura solo para staff.
"""
import pytest

URLS_REPORTES = [
    "/api/v1/reportes/dashboard/",
    "/api/v1/reportes/ventas/",
    "/api/v1/reportes/inventario/",
    "/api/v1/reportes/videojuegos/",
]

URLS_CATALOGO_PUBLICO = [
    "/api/v1/catalogo/videojuegos/",
    "/api/v1/catalogo/categorias/",
    "/api/v1/catalogo/plataformas/",
    "/api/v1/catalogo/generos/",
]

URLS_AUTENTICADAS = [
    "/api/v1/pedidos/",
    "/api/v1/pedidos/carrito/",
    "/api/v1/auth/me/",
]


@pytest.mark.django_db
@pytest.mark.parametrize("url", URLS_REPORTES)
def test_visitante_no_puede_acceder_a_reportes(api_client, url):
    response = api_client.get(url)
    assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize("url", URLS_REPORTES)
def test_cliente_sin_staff_no_puede_acceder_a_reportes(api_cliente, url):
    response = api_cliente.get(url)
    assert response.status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize("url", URLS_REPORTES)
def test_admin_puede_acceder_a_reportes(api_admin, url):
    response = api_admin.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("url", URLS_CATALOGO_PUBLICO)
def test_catalogo_es_publico_para_lectura(api_client, url):
    response = api_client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("url", URLS_AUTENTICADAS)
def test_rutas_privadas_rechazan_visitantes(api_client, url):
    response = api_client.get(url)
    assert response.status_code == 401


@pytest.mark.django_db
def test_cliente_puede_ver_su_perfil(api_cliente, usuario_cliente):
    response = api_cliente.get("/api/v1/auth/me/")
    assert response.status_code == 200
    assert response.data["username"] == usuario_cliente.username


def _payload_videojuego(categoria, plataforma, genero):
    return {
        "titulo": "Juego Nuevo",
        "descripcion": "Descripción",
        "precio": "50000.00",
        "stock": 3,
        "categoria_id": categoria.pk,
        "plataforma_id": plataforma.pk,
        "genero_id": genero.pk,
    }


@pytest.mark.django_db
def test_visitante_no_puede_crear_videojuegos(
    api_client, categoria, plataforma, genero
):
    response = api_client.post(
        "/api/v1/catalogo/videojuegos/",
        _payload_videojuego(categoria, plataforma, genero),
        format="json",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_cliente_no_puede_crear_videojuegos(
    api_cliente, categoria, plataforma, genero
):
    response = api_cliente.post(
        "/api/v1/catalogo/videojuegos/",
        _payload_videojuego(categoria, plataforma, genero),
        format="json",
    )
    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_puede_crear_videojuegos(api_admin, categoria, plataforma, genero):
    response = api_admin.post(
        "/api/v1/catalogo/videojuegos/",
        _payload_videojuego(categoria, plataforma, genero),
        format="json",
    )
    assert response.status_code == 201
    assert response.data["titulo"] == "Juego Nuevo"
