"""
Pruebas de las migraciones del catálogo comercial (AZ-S1-13):
  - Desde cero: la cadena completa de migraciones aplica limpiamente.
  - Sobre el esquema existente: precio/stock/plataforma se trasladan desde
    Videojuego a la oferta y los detalles históricos quedan referenciando
    la oferta adquirida, conservando el precio unitario y los snapshots.
"""
from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from catalogo.models import (
    Categoria,
    Genero,
    OfertaVideojuego,
    Plataforma,
    Videojuego,
)
from pedidos.models import DetallePedido, Pedido

ANTES = [("catalogo", "0001_initial"), ("pedidos", "0001_initial")]
DESPUES = [
    ("catalogo", "0002_ofertavideojuego"),
    ("pedidos", "0002_detallepedido_oferta"),
]


def _migrate(targets=None):
    """Aplica o desaplica migraciones; sin targets aplica todo hasta la más reciente."""
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    if targets is None:
        targets = executor.loader.graph.leaf_nodes()
    executor.migrate(targets)
    return executor


def _apps_at(migration_nodes):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    return executor.loader.project_state(migration_nodes).apps


@pytest.mark.django_db(transaction=True)
def test_migracion_traslada_precio_y_stock_a_la_oferta():
    """El esquema existente migra sin perder precio, stock ni plataforma."""
    # Regresar al esquema antiguo y crear datos con los modelos históricos.
    _migrate(ANTES)
    apps_viejo = _apps_at(ANTES)
    Categoria = apps_viejo.get_model("catalogo", "Categoria")
    Genero = apps_viejo.get_model("catalogo", "Genero")
    Plataforma = apps_viejo.get_model("catalogo", "Plataforma")
    VideojuegoViejo = apps_viejo.get_model("catalogo", "Videojuego")

    categoria = Categoria.objects.create(nombre="Acción")
    genero = Genero.objects.create(nombre="RPG")
    plataforma = Plataforma.objects.create(nombre="PC")
    vj = VideojuegoViejo.objects.create(
        titulo="Juego Legado",
        precio=Decimal("12345.00"),
        stock=7,
        activo=True,
        categoria=categoria,
        plataforma=plataforma,
        genero=genero,
    )

    # Aplicar la normalización del catálogo.
    _migrate(DESPUES)

    oferta = OfertaVideojuego.objects.get(videojuego__titulo="Juego Legado")
    assert oferta.precio_vigente == Decimal("12345.00")
    assert oferta.stock == 7
    assert oferta.plataforma.nombre == "PC"
    assert oferta.sku == f"AZ-{vj.pk:04d}-{plataforma.pk:03d}"
    assert oferta.esta_publicada is True


@pytest.mark.django_db(transaction=True)
def test_migracion_traslada_estado_no_publicado(usuario_cliente):
    """Un videojuego inactivo se traslada como oferta retirada."""
    _migrate(ANTES)
    apps_viejo = _apps_at(ANTES)
    Categoria = apps_viejo.get_model("catalogo", "Categoria")
    Genero = apps_viejo.get_model("catalogo", "Genero")
    Plataforma = apps_viejo.get_model("catalogo", "Plataforma")
    VideojuegoViejo = apps_viejo.get_model("catalogo", "Videojuego")

    vj = VideojuegoViejo.objects.create(
        titulo="Juego Retirado",
        precio=Decimal("1000.00"),
        stock=1,
        activo=False,
        categoria=Categoria.objects.create(nombre="Deportes"),
        plataforma=Plataforma.objects.create(nombre="Xbox"),
        genero=Genero.objects.create(nombre="Shooter"),
    )

    _migrate(DESPUES)

    oferta = OfertaVideojuego.objects.get(videojuego__titulo="Juego Retirado")
    assert oferta.estado_publicacion == OfertaVideojuego.EstadoPublicacion.RETIRADO
    assert vj.pk is not None


@pytest.mark.django_db(transaction=True)
def test_migracion_reasigna_detalles_a_la_oferta(usuario_cliente):
    """Los detalles históricos referencian la oferta y conservan su precio."""
    _migrate(ANTES)
    apps_viejo = _apps_at(ANTES)
    VideojuegoViejo = apps_viejo.get_model("catalogo", "Videojuego")
    PedidoViejo = apps_viejo.get_model("pedidos", "Pedido")
    DetalleViejo = apps_viejo.get_model("pedidos", "DetallePedido")

    # Catálogo y pedido con el esquema antiguo.
    vj = VideojuegoViejo.objects.create(
        titulo="Juego Comprado",
        precio=Decimal("50000.00"),
        stock=4,
        activo=True,
        categoria=_get_viejo(apps_viejo, "Categoria", nombre="Acción"),
        plataforma=_get_viejo(apps_viejo, "Plataforma", nombre="PC"),
        genero=_get_viejo(apps_viejo, "Genero", nombre="RPG"),
    )
    # El usuario vive en la tabla de cuentas (nunca se revierte), pero la
    # clase histórica de Pedido espera la clase histórica de Usuario: se
    # asigna por id para eludir la comprobación de tipo en Python.
    pedido_viejo = PedidoViejo.objects.create(
        cliente_id=usuario_cliente.pk, estado="pagado"
    )
    DetalleViejo.objects.create(
        pedido=pedido_viejo,
        videojuego=vj,
        cantidad=2,
        precio_unitario=Decimal("45000.00"),  # precio histórico distinto
    )

    _migrate(DESPUES)

    pedido = Pedido.objects.get(pk=pedido_viejo.pk)
    detalle = pedido.detalles.get()
    assert detalle.oferta.videojuego.titulo == "Juego Comprado"
    assert detalle.oferta.precio_vigente == Decimal("50000.00")
    # El detalle conserva su precio unitario histórico y congela el snapshot.
    assert detalle.precio_unitario == Decimal("45000.00")
    assert detalle.titulo_snapshot == "Juego Comprado"
    assert detalle.plataforma_snapshot == "PC"
    assert detalle.cantidad == 2


@pytest.mark.django_db(transaction=True)
def test_migraciones_desde_cero_aplican_limpio(usuario_cliente):
    """La cadena completa se aplica limpiamente sobre una base vacía."""
    # Desaplicar todo lo que depende del catálogo (arrastra pedidos y pagos).
    _migrate([("catalogo", None), ("pedidos", None), ("pagos", None)])

    # Las tablas del catálogo comercial ya no existen: se verifica por
    # introspección porque el ORM no puede consultar tablas ausentes.
    tablas = connection.introspection.table_names()
    assert "catalogo_videojuego" not in tablas
    assert "catalogo_ofertavideojuego" not in tablas
    assert "pedidos_detallepedido" not in tablas

    # Aplicar de nuevo toda la cadena desde cero (todas las apps al estado
    # más reciente) y operar normalmente sobre el esquema resultante.
    _migrate()

    categoria = Categoria.objects.create(nombre="Acción")
    genero = Genero.objects.create(nombre="RPG")
    plataforma = Plataforma.objects.create(nombre="PC")
    videojuego = Videojuego.objects.create(
        titulo="Juego Desde Cero", categoria=categoria, genero=genero
    )
    oferta = OfertaVideojuego.objects.create(
        videojuego=videojuego,
        plataforma=plataforma,
        precio_vigente=Decimal("1000.00"),
        sku="AZ-CERO-001",
        stock=2,
    )
    pedido = Pedido.objects.create(
        cliente=usuario_cliente, estado=Pedido.Estado.PENDIENTE
    )
    detalle = DetallePedido.objects.create(
        pedido=pedido, oferta=oferta, cantidad=1,
        precio_unitario=oferta.precio_vigente,
    )
    assert detalle.titulo_snapshot == "Juego Desde Cero"
    assert detalle.plataforma_snapshot == "PC"


@pytest.mark.django_db(transaction=True)
def test_migracion_reversible_sobre_datos_poblados(usuario_cliente):
    """
    La reversión sobre una base de datos poblada restaura el esquema legacy
    y devuelve los datos desde las ofertas (AZ-S1-13).
    """
    _migrate(ANTES)
    apps_viejo = _apps_at(ANTES)
    VideojuegoViejo = apps_viejo.get_model("catalogo", "Videojuego")
    PedidoViejo = apps_viejo.get_model("pedidos", "Pedido")
    DetalleViejo = apps_viejo.get_model("pedidos", "DetallePedido")

    vj = VideojuegoViejo.objects.create(
        titulo="Juego Volátil",
        precio=Decimal("12345.00"),
        stock=7,
        activo=True,
        categoria=_get_viejo(apps_viejo, "Categoria", nombre="Acción"),
        plataforma=_get_viejo(apps_viejo, "Plataforma", nombre="PC"),
        genero=_get_viejo(apps_viejo, "Genero", nombre="RPG"),
    )
    pedido_viejo = PedidoViejo.objects.create(
        cliente_id=usuario_cliente.pk, estado="pagado"
    )
    DetalleViejo.objects.create(
        pedido=pedido_viejo,
        videojuego=vj,
        cantidad=2,
        precio_unitario=Decimal("45000.00"),
    )

    # Normalizar y EVOLUCIONAR el catálogo: la oferta cambia de precio/stock.
    _migrate(DESPUES)
    oferta = OfertaVideojuego.objects.get(videojuego__titulo="Juego Volátil")
    oferta.precio_vigente = Decimal("99999.00")
    oferta.stock = 3
    oferta.save()

    # Reversión sobre datos ya poblados.
    _migrate(ANTES)

    # El esquema legacy se restauró y los datos volvieron desde la oferta.
    apps_legacy = _apps_at(ANTES)
    VideojuegoLegacy = apps_legacy.get_model("catalogo", "Videojuego")
    DetalleLegacy = apps_legacy.get_model("pedidos", "DetallePedido")

    vj_legacy = VideojuegoLegacy.objects.get(pk=vj.pk)
    assert vj_legacy.precio == Decimal("99999.00")
    assert vj_legacy.stock == 3
    assert vj_legacy.plataforma.nombre == "PC"

    detalle_legacy = DetalleLegacy.objects.get(pedido_id=pedido_viejo.pk)
    assert detalle_legacy.videojuego.pk == vj.pk
    assert detalle_legacy.precio_unitario == Decimal("45000.00")

    # La cadena vuelve a aplicar limpiamente tras la reversión.
    _migrate()


def _get_viejo(apps, model_name, **kwargs):
    return apps.get_model("catalogo", model_name).objects.get_or_create(**kwargs)[0]
