"""Fixtures compartidos para toda la suite de pruebas."""
import uuid

import pytest
from decimal import Decimal

from catalogo.models import Categoria, Genero, OfertaVideojuego, Plataforma, Videojuego
from cuentas.models import Rol, Usuario
from inventario.models import (
    MotivoMovimientoInventario,
    MovimientoInventarioOfertaVideojuego,
    TipoMovimientoInventario,
)
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


# ── Catálogo ─────────────────────────────────────────────────────────────────

@pytest.fixture
def categoria(db):
    return Categoria.objects.create(nombre="Acción")


@pytest.fixture
def plataforma(db):
    return Plataforma.objects.create(nombre="PC")


@pytest.fixture
def plataforma_alternativa(db):
    return Plataforma.objects.create(nombre="PlayStation 5")


@pytest.fixture
def genero(db):
    return Genero.objects.create(nombre="RPG")


@pytest.fixture
def videojuego(db, categoria, genero):
    return Videojuego.objects.create(
        titulo="Juego Alpha",
        activo=True,
        categoria=categoria,
        genero=genero,
    )


@pytest.fixture
def oferta(db, videojuego, plataforma):
    """Oferta publicada con stock: la unidad vendible por defecto."""
    return OfertaVideojuego.objects.create(
        videojuego=videojuego,
        plataforma=plataforma,
        precio_vigente=Decimal("80000"),
        stock=10,
        sku="AZ-0001-001",
        estado_publicacion=OfertaVideojuego.EstadoPublicacion.PUBLICADO,
    )


@pytest.fixture
def oferta_agotada(db, videojuego, plataforma):
    """Oferta publicada pero sin stock."""
    return OfertaVideojuego.objects.create(
        videojuego=videojuego,
        plataforma=plataforma,
        precio_vigente=Decimal("60000"),
        stock=0,
        sku="AZ-0002-001",
        estado_publicacion=OfertaVideojuego.EstadoPublicacion.PUBLICADO,
    )


# ── Pedido con un ítem ────────────────────────────────────────────────────────

@pytest.fixture
def pedido_con_item(db, usuario_cliente, oferta):
    pedido = Pedido.objects.create(cliente=usuario_cliente, estado=Pedido.Estado.PENDIENTE)
    DetallePedido.objects.create(
        pedido=pedido,
        oferta=oferta,
        cantidad=2,
        precio_unitario=oferta.precio_vigente,
    )
    return pedido


# ── Inventario (AZ-S1-14) ──────────────────────────────────────────────────────


@pytest.fixture
def tipo_entrada(db):
    """Tipo de movimiento de entrada (get_or_create: tolera la semilla 0002)."""
    return TipoMovimientoInventario.objects.get_or_create(
        codigo="ENTRADA",
        defaults={"nombre": "Entrada", "naturaleza": "entrada"},
    )[0]


@pytest.fixture
def tipo_salida(db):
    return TipoMovimientoInventario.objects.get_or_create(
        codigo="SALIDA",
        defaults={"nombre": "Salida", "naturaleza": "salida"},
    )[0]


@pytest.fixture
def tipo_ajuste(db):
    return TipoMovimientoInventario.objects.get_or_create(
        codigo="AJUSTE",
        defaults={"nombre": "Ajuste", "naturaleza": "ajuste"},
    )[0]


@pytest.fixture
def motivo_venta(db):
    return MotivoMovimientoInventario.objects.get_or_create(
        codigo="VENTA", defaults={"nombre": "Venta"}
    )[0]


@pytest.fixture
def movimiento_entrada(oferta, tipo_entrada):
    """Movimiento válido del ledger sobre la oferta con stock 10."""
    return MovimientoInventarioOfertaVideojuego.objects.create(
        oferta=oferta,
        tipo_movimiento=tipo_entrada,
        cantidad=5,
        saldo_anterior=10,
        saldo_posterior=15,
        clave_idempotencia=f"test-entrada-{uuid.uuid4()}",
    )
