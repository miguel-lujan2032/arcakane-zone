"""Fixtures compartidos para toda la suite de pruebas."""
import pytest
from decimal import Decimal

from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from catalogo.models import Categoria, Genero, Plataforma, Videojuego
from cuentas.models import Rol, Usuario
from pedidos.models import DetallePedido, Pedido


# ── Roles ────────────────────────────────────────────────────────────────────

@pytest.fixture
def rol_cliente(db):
    return Rol.objects.create(nombre="cliente")


@pytest.fixture
def rol_admin(db):
    return Rol.objects.create(nombre="administrador")


# ── Usuarios ─────────────────────────────────────────────────────────────────

@pytest.fixture
def usuario_cliente(db, rol_cliente):
    u = Usuario.objects.create_user(
        username="cliente_test",
        password="pass1234!",
        email="cliente@test.com",
        rol=rol_cliente,
    )
    return u


@pytest.fixture
def usuario_admin(db, rol_admin):
    u = Usuario.objects.create_user(
        username="admin_test",
        password="pass1234!",
        email="admin@test.com",
        rol=rol_admin,
        is_staff=True,
    )
    return u


# ── Clientes de API ──────────────────────────────────────────────────────────

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def api_cliente(usuario_cliente):
    client = APIClient()
    token, _ = Token.objects.get_or_create(user=usuario_cliente)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def api_admin(usuario_admin):
    client = APIClient()
    token, _ = Token.objects.get_or_create(user=usuario_admin)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


# ── Catálogo ─────────────────────────────────────────────────────────────────

@pytest.fixture
def categoria(db):
    return Categoria.objects.create(nombre="Acción")


@pytest.fixture
def plataforma(db):
    return Plataforma.objects.create(nombre="PC")


@pytest.fixture
def genero(db):
    return Genero.objects.create(nombre="RPG")


@pytest.fixture
def videojuego(db, categoria, plataforma, genero):
    return Videojuego.objects.create(
        titulo="Juego Alpha",
        precio=Decimal("80000"),
        stock=10,
        activo=True,
        categoria=categoria,
        plataforma=plataforma,
        genero=genero,
    )


@pytest.fixture
def videojuego_agotado(db, categoria, plataforma, genero):
    return Videojuego.objects.create(
        titulo="Juego Agotado",
        precio=Decimal("60000"),
        stock=0,
        activo=True,
        categoria=categoria,
        plataforma=plataforma,
        genero=genero,
    )


# ── Pedido con un ítem ────────────────────────────────────────────────────────

@pytest.fixture
def pedido_con_item(db, usuario_cliente, videojuego):
    pedido = Pedido.objects.create(cliente=usuario_cliente, estado=Pedido.Estado.PENDIENTE)
    DetallePedido.objects.create(
        pedido=pedido,
        videojuego=videojuego,
        cantidad=2,
        precio_unitario=videojuego.precio,
    )
    return pedido
