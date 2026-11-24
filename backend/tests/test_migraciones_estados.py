"""
Pruebas de las migraciones de normalización de estados (AZ-S1-17).

Cubre: migración desde el esquema anterior con datos (cada estado termina en su
FK equivalente), valor desconocido aborta con mensaje claro y reversión con
datos hasta el esquema anterior.
"""
from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

# Modelos actuales solo donde aplica; para estados intermedios se usan apps históricos.


ANTES_PEDIDOS = [("pedidos", "0003_integridad_detallepedido")]
DESPUES_PEDIDOS = [("pedidos", "0008_pedido_estado_definitivo")]

ANTES_PAGOS = [("pagos", "0002_integridad_pagos")]
DESPUES_PAGOS = [("pagos", "0007_pago_estado_definitivo")]

ANTES_CATALOGO = [("catalogo", "0007_retirar_fks_categoria_genero")]
DESPUES_CATALOGO = [("catalogo", "0012_oferta_estado_definitivo")]

# Para crear datos coherentes con el esquema anterior, las apps relacionadas
# deben estar en estados compatibles.
BASE_PARA_PEDIDOS = [
    ("catalogo", "0007_retirar_fks_categoria_genero"),
    ("pedidos", "0003_integridad_detallepedido"),
    ("pagos", "0002_integridad_pagos"),
]
BASE_PARA_PAGOS = BASE_PARA_PEDIDOS
BASE_PARA_CATALOGO = BASE_PARA_PEDIDOS


def _migrate(targets=None):
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
def test_migracion_pedidos_con_datos_convierte_todos_los_estados(usuario_cliente):
    _migrate(BASE_PARA_PEDIDOS)
    apps = _apps_at(BASE_PARA_PEDIDOS)
    PedidoViejo = apps.get_model("pedidos", "Pedido")

    ids = {}
    for estado in ("pendiente", "pagado", "cancelado"):
        ids[estado] = PedidoViejo.objects.create(
            cliente_id=usuario_cliente.pk, estado=estado
        ).pk

    _migrate(DESPUES_PEDIDOS)
    apps_final = _apps_at(DESPUES_PEDIDOS)
    PedidoFinal = apps_final.get_model("pedidos", "Pedido")

    for estado, pk in ids.items():
        pedido = PedidoFinal.objects.get(pk=pk)
        assert pedido.estado_id == estado
        assert pedido.estado.codigo == estado

    _migrate()


@pytest.mark.django_db(transaction=True)
def test_migracion_pagos_con_datos_convierte_todos_los_estados(
    usuario_cliente, oferta
):
    _migrate(BASE_PARA_PAGOS)
    apps = _apps_at(BASE_PARA_PAGOS)
    PedidoViejo = apps.get_model("pedidos", "Pedido")
    PagoViejo = apps.get_model("pagos", "Pago")

    ids = {}
    for i, estado in enumerate(("aprobado", "rechazado", "pendiente"), start=1):
        pedido = PedidoViejo.objects.create(
            cliente_id=usuario_cliente.pk, estado="pendiente"
        )
        ids[estado] = PagoViejo.objects.create(
            pedido_id=pedido.pk, monto=Decimal(f"{i}.00"), estado=estado
        ).pk

    _migrate(DESPUES_PAGOS)
    apps_final = _apps_at(DESPUES_PAGOS)
    PagoFinal = apps_final.get_model("pagos", "Pago")

    for estado, pk in ids.items():
        pago = PagoFinal.objects.get(pk=pk)
        assert pago.estado_id == estado
        assert pago.estado.codigo == estado

    _migrate()


@pytest.mark.django_db(transaction=True)
def test_migracion_catalogo_con_datos_convierte_estados_publicacion():
    _migrate(BASE_PARA_CATALOGO)
    apps = _apps_at(BASE_PARA_CATALOGO)
    Categoria = apps.get_model("catalogo", "Categoria")
    Genero = apps.get_model("catalogo", "Genero")
    Plataforma = apps.get_model("catalogo", "Plataforma")
    Videojuego = apps.get_model("catalogo", "Videojuego")
    OfertaVieja = apps.get_model("catalogo", "OfertaVideojuego")

    cat = Categoria.objects.create(nombre="Cat")
    gen = Genero.objects.create(nombre="Gen")
    vj = Videojuego.objects.create(titulo="Juego", activo=True)
    # Esquema anterior (0007): Videojuego usa M2M via tablas puente ya creadas.
    apps.get_model("catalogo", "VideojuegoCategoria").objects.create(
        videojuego=vj, categoria=cat
    )
    apps.get_model("catalogo", "VideojuegoGenero").objects.create(
        videojuego=vj, genero=gen
    )

    ids = {}
    for i, estado in enumerate(("borrador", "publicado", "retirado"), start=1):
        plat = Plataforma.objects.create(nombre=f"P{i}")
        ids[estado] = OfertaVieja.objects.create(
            videojuego=vj,
            plataforma=plat,
            precio_vigente=Decimal("10.00"),
            sku=f"AZ-EST-{i}",
            stock=1,
            estado_publicacion=estado,
        ).pk

    _migrate(DESPUES_CATALOGO)
    apps_final = _apps_at(DESPUES_CATALOGO)
    OfertaFinal = apps_final.get_model("catalogo", "OfertaVideojuego")

    for estado, pk in ids.items():
        oferta = OfertaFinal.objects.get(pk=pk)
        assert oferta.estado_publicacion_id == estado
        assert oferta.estado_publicacion.codigo == estado

    _migrate()


@pytest.mark.django_db(transaction=True)
def test_migracion_pedidos_aborta_con_valor_desconocido(usuario_cliente):
    _migrate(BASE_PARA_PEDIDOS)
    apps = _apps_at(BASE_PARA_PEDIDOS)
    PedidoViejo = apps.get_model("pedidos", "Pedido")

    pedido_malo = PedidoViejo.objects.create(
        cliente_id=usuario_cliente.pk, estado="desconocido"
    )

    with pytest.raises(RuntimeError) as excinfo:
        _migrate(DESPUES_PEDIDOS)

    mensaje = str(excinfo.value)
    assert "pedidos_pedido" in mensaje
    assert "estado" in mensaje
    assert "desconocido" in mensaje
    assert "1 filas" in mensaje

    # Limpieza: volver al esquema anterior, eliminar dato inválido y restaurar hojas.
    _migrate(BASE_PARA_PEDIDOS)
    apps_limpieza = _apps_at(BASE_PARA_PEDIDOS)
    apps_limpieza.get_model("pedidos", "Pedido").objects.filter(pk=pedido_malo.pk).delete()
    _migrate()


@pytest.mark.django_db(transaction=True)
def test_migracion_pagos_aborta_con_valor_desconocido(usuario_cliente):
    _migrate(BASE_PARA_PAGOS)
    apps = _apps_at(BASE_PARA_PAGOS)
    PedidoViejo = apps.get_model("pedidos", "Pedido")
    PagoViejo = apps.get_model("pagos", "Pago")

    pedido = PedidoViejo.objects.create(cliente_id=usuario_cliente.pk, estado="pendiente")
    pago_malo = PagoViejo.objects.create(
        pedido_id=pedido.pk, monto=Decimal("10.00"), estado="desconocido"
    )

    with pytest.raises(RuntimeError) as excinfo:
        _migrate(DESPUES_PAGOS)

    mensaje = str(excinfo.value)
    assert "pagos_pago" in mensaje
    assert "estado" in mensaje
    assert "desconocido" in mensaje
    assert "1 filas" in mensaje

    _migrate(BASE_PARA_PAGOS)
    apps_limpieza = _apps_at(BASE_PARA_PAGOS)
    apps_limpieza.get_model("pagos", "Pago").objects.filter(pk=pago_malo.pk).delete()
    apps_limpieza.get_model("pedidos", "Pedido").objects.filter(pk=pedido.pk).delete()
    _migrate()


@pytest.mark.django_db(transaction=True)
def test_migracion_catalogo_aborta_con_valor_desconocido():
    _migrate(BASE_PARA_CATALOGO)
    apps = _apps_at(BASE_PARA_CATALOGO)
    Categoria = apps.get_model("catalogo", "Categoria")
    Genero = apps.get_model("catalogo", "Genero")
    Plataforma = apps.get_model("catalogo", "Plataforma")
    Videojuego = apps.get_model("catalogo", "Videojuego")
    OfertaVieja = apps.get_model("catalogo", "OfertaVideojuego")

    cat = Categoria.objects.create(nombre="Cat")
    gen = Genero.objects.create(nombre="Gen")
    plat = Plataforma.objects.create(nombre="PC")
    vj = Videojuego.objects.create(titulo="Juego", activo=True)
    apps.get_model("catalogo", "VideojuegoCategoria").objects.create(
        videojuego=vj, categoria=cat
    )
    apps.get_model("catalogo", "VideojuegoGenero").objects.create(
        videojuego=vj, genero=gen
    )
    oferta_mala = OfertaVieja.objects.create(
        videojuego=vj,
        plataforma=plat,
        precio_vigente=Decimal("10.00"),
        sku="AZ-UNK-1",
        stock=1,
        estado_publicacion="desconocido",
    )

    with pytest.raises(RuntimeError) as excinfo:
        _migrate(DESPUES_CATALOGO)

    mensaje = str(excinfo.value)
    assert "catalogo_ofertavideojuego" in mensaje
    assert "estado_publicacion" in mensaje
    assert "desconocido" in mensaje
    assert "1 filas" in mensaje

    _migrate(BASE_PARA_CATALOGO)
    apps_limpieza = _apps_at(BASE_PARA_CATALOGO)
    OfertaV = apps_limpieza.get_model("catalogo", "OfertaVideojuego")
    OfertaV.objects.filter(pk=oferta_mala.pk).delete()
    apps_limpieza.get_model("catalogo", "VideojuegoCategoria").objects.all().delete()
    apps_limpieza.get_model("catalogo", "VideojuegoGenero").objects.all().delete()
    apps_limpieza.get_model("catalogo", "Videojuego").objects.filter(pk=vj.pk).delete()
    apps_limpieza.get_model("catalogo", "Plataforma").objects.filter(pk=plat.pk).delete()
    apps_limpieza.get_model("catalogo", "Genero").objects.filter(pk=gen.pk).delete()
    apps_limpieza.get_model("catalogo", "Categoria").objects.filter(pk=cat.pk).delete()
    _migrate()


@pytest.mark.django_db(transaction=True)
def test_reversion_pedidos_con_datos_hasta_esquema_anterior(usuario_cliente):
    _migrate(BASE_PARA_PEDIDOS)
    apps = _apps_at(BASE_PARA_PEDIDOS)
    PedidoViejo = apps.get_model("pedidos", "Pedido")
    pk = PedidoViejo.objects.create(
        cliente_id=usuario_cliente.pk, estado="pagado"
    ).pk

    _migrate(DESPUES_PEDIDOS)
    apps_final = _apps_at(DESPUES_PEDIDOS)
    assert apps_final.get_model("pedidos", "Pedido").objects.get(pk=pk).estado_id == "pagado"

    _migrate(BASE_PARA_PEDIDOS)
    apps_viejo = _apps_at(BASE_PARA_PEDIDOS)
    PedidoViejo = apps_viejo.get_model("pedidos", "Pedido")
    pedido = PedidoViejo.objects.get(pk=pk)
    assert pedido.estado == "pagado"

    # La cadena vuelve a aplicar limpiamente.
    _migrate()


@pytest.mark.django_db(transaction=True)
def test_reversion_catalogo_y_pagos_con_datos(usuario_cliente):
    _migrate(BASE_PARA_PAGOS)
    apps = _apps_at(BASE_PARA_PAGOS)
    PedidoViejo = apps.get_model("pedidos", "Pedido")
    PagoViejo = apps.get_model("pagos", "Pago")
    Categoria = apps.get_model("catalogo", "Categoria")
    Genero = apps.get_model("catalogo", "Genero")
    Plataforma = apps.get_model("catalogo", "Plataforma")
    Videojuego = apps.get_model("catalogo", "Videojuego")
    OfertaVieja = apps.get_model("catalogo", "OfertaVideojuego")

    pedido = PedidoViejo.objects.create(cliente_id=usuario_cliente.pk, estado="cancelado")
    pago_pk = PagoViejo.objects.create(
        pedido_id=pedido.pk, monto=Decimal("5.00"), estado="rechazado"
    ).pk
    cat = Categoria.objects.create(nombre="CatR")
    gen = Genero.objects.create(nombre="GenR")
    plat = Plataforma.objects.create(nombre="PCR")
    vj = Videojuego.objects.create(titulo="JuegoR", activo=False)
    apps.get_model("catalogo", "VideojuegoCategoria").objects.create(
        videojuego=vj, categoria=cat
    )
    apps.get_model("catalogo", "VideojuegoGenero").objects.create(
        videojuego=vj, genero=gen
    )
    oferta_pk = OfertaVieja.objects.create(
        videojuego=vj,
        plataforma=plat,
        precio_vigente=Decimal("7.00"),
        sku="AZ-REV-1",
        stock=2,
        estado_publicacion="retirado",
    ).pk

    _migrate()
    from catalogo.models import OfertaVideojuego
    from pagos.models import IntentoPago
    from pedidos.models import Pedido

    assert Pedido.objects.get(pk=pedido.pk).estado_id == "cancelado"
    assert IntentoPago.objects.get(pk=pago_pk).estado_id == "rechazado"
    assert OfertaVideojuego.objects.get(pk=oferta_pk).estado_publicacion_id == "retirado"

    _migrate(BASE_PARA_PAGOS)

    apps_viejo = _apps_at(BASE_PARA_PAGOS)
    assert apps_viejo.get_model("pedidos", "Pedido").objects.get(pk=pedido.pk).estado == "cancelado"
    assert apps_viejo.get_model("pagos", "Pago").objects.get(pk=pago_pk).estado == "rechazado"
    assert (
        apps_viejo.get_model("catalogo", "OfertaVideojuego")
        .objects.get(pk=oferta_pk)
        .estado_publicacion
        == "retirado"
    )

    _migrate()
