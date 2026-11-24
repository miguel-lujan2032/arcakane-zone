"""
Pruebas de migraciones del ciclo transaccional (AZ-S1-19).

Cubre avance y reversión entre el esquema anterior (pedidos 0008, pagos 0007)
y el esquema normalizado, incluyendo abortos descriptivos.
"""
from decimal import Decimal

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


ANTES = [
    ("pedidos", "0008_pedido_estado_definitivo"),
    ("pagos", "0007_pago_estado_definitivo"),
    ("catalogo", "0012_oferta_estado_definitivo"),
    ("cuentas", "0007_usuario_roles_m2m"),
    ("inventario", "0001_initial"),
]

DESPUES = None  # hojas


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


def _crear_base(apps, usuario_cliente, oferta, *, n_pedidos=1):
    Pedido = apps.get_model("pedidos", "Pedido")
    pedidos = []
    for _ in range(n_pedidos):
        pedidos.append(Pedido.objects.create(cliente_id=usuario_cliente.pk, estado_id="pendiente"))
    return pedidos


@pytest.mark.django_db(transaction=True)
def test_migracion_backfill_referencias_vacias_y_historial_inicial(usuario_cliente, oferta):
    """Referencias vacías se rellenan determinísticamente y cada pedido queda con historial."""
    _migrate(ANTES)
    apps = _apps_at(ANTES)
    Pedido = apps.get_model("pedidos", "Pedido")
    Pago = apps.get_model("pagos", "Pago")
    Venta = apps.get_model("pagos", "Venta")

    p1 = Pedido.objects.create(cliente_id=usuario_cliente.pk, estado_id="pendiente")
    p2 = Pedido.objects.create(cliente_id=usuario_cliente.pk, estado_id="pagado")
    pago1 = Pago.objects.create(
        pedido_id=p1.pk, monto=Decimal("10.00"), estado_id="pendiente", referencia=""
    )
    pago2 = Pago.objects.create(
        pedido_id=p2.pk, monto=Decimal("20.00"), estado_id="aprobado", referencia=""
    )
    Venta.objects.create(pedido_id=p2.pk, total=Decimal("20.00"))

    _migrate(DESPUES)

    from pagos.models import IntentoPago
    from pedidos.models import HistorialEstadoPedido, Pedido as PedidoActual

    i1 = IntentoPago.objects.get(pk=pago1.pk)
    i2 = IntentoPago.objects.get(pk=pago2.pk)
    assert i1.referencia == f"LEGACY-{pago1.pk}"
    assert i2.referencia == f"LEGACY-{pago2.pk}"
    assert i1.importe == Decimal("10.00")
    assert i2.importe == Decimal("20.00")

    # Cada pedido existente tiene historial inicial.
    for p in (p1, p2):
        actual = PedidoActual.objects.get(pk=p.pk)
        h = HistorialEstadoPedido.objects.filter(pedido_id=p.pk)
        assert h.count() == 1
        assert h.first().estado_id == actual.estado_id
        assert h.first().actor_id is None
        assert "Estado vigente al migrar (AZ-S1-19)" in h.first().observacion


@pytest.mark.django_db(transaction=True)
def test_migracion_aborta_con_referencias_duplicadas_no_vacias(usuario_cliente):
    _migrate(ANTES)
    apps = _apps_at(ANTES)
    Pedido = apps.get_model("pedidos", "Pedido")
    Pago = apps.get_model("pagos", "Pago")

    p1 = Pedido.objects.create(cliente_id=usuario_cliente.pk, estado_id="pendiente")
    p2 = Pedido.objects.create(cliente_id=usuario_cliente.pk, estado_id="pendiente")
    Pago.objects.create(pedido_id=p1.pk, monto=Decimal("10.00"), estado_id="pendiente", referencia="DUP")
    Pago.objects.create(pedido_id=p2.pk, monto=Decimal("10.00"), estado_id="pendiente", referencia="DUP")

    with pytest.raises(RuntimeError) as excinfo:
        _migrate(DESPUES)

    msg = str(excinfo.value)
    assert "pagos_intentopago" in msg
    assert "referencia" in msg
    assert "DUP" in msg
    assert "duplicado" in msg

    # Limpieza para teardown.
    _migrate(ANTES)
    apps_l = _apps_at(ANTES)
    apps_l.get_model("pagos", "Pago").objects.filter(referencia="DUP").delete()
    apps_l.get_model("pedidos", "Pedido").objects.filter(pk__in=[p1.pk, p2.pk]).delete()
    _migrate()


@pytest.mark.django_db(transaction=True)
def test_migracion_aborta_si_venta_sin_intento_aprobado(usuario_cliente):
    _migrate(ANTES)
    apps = _apps_at(ANTES)
    Pedido = apps.get_model("pedidos", "Pedido")
    Pago = apps.get_model("pagos", "Pago")
    Venta = apps.get_model("pagos", "Venta")

    p = Pedido.objects.create(cliente_id=usuario_cliente.pk, estado_id="pagado")
    # Intento rechazado (no aprobado) + venta existente.
    Pago.objects.create(
        pedido_id=p.pk, monto=Decimal("30.00"), estado_id="rechazado", referencia="R1"
    )
    Venta.objects.create(pedido_id=p.pk, total=Decimal("30.00"))

    with pytest.raises(RuntimeError) as excinfo:
        _migrate(DESPUES)

    msg = str(excinfo.value)
    assert "pagos_venta" in msg
    assert "intento_aprobado" in msg
    assert "sin intento aprobado" in msg

    _migrate(ANTES)
    apps_l = _apps_at(ANTES)
    apps_l.get_model("pagos", "Venta").objects.filter(pedido_id=p.pk).delete()
    apps_l.get_model("pagos", "Pago").objects.filter(pedido_id=p.pk).delete()
    apps_l.get_model("pedidos", "Pedido").objects.filter(pk=p.pk).delete()
    _migrate()


@pytest.mark.django_db(transaction=True)
def test_reversion_con_datos_hasta_esquema_anterior(usuario_cliente):
    """Migrar adelante y revertir a pagos 0007/pedidos 0008 conserva datos válidos."""
    _migrate(ANTES)
    apps = _apps_at(ANTES)
    Pedido = apps.get_model("pedidos", "Pedido")
    Pago = apps.get_model("pagos", "Pago")
    Venta = apps.get_model("pagos", "Venta")

    p_pagado = Pedido.objects.create(cliente_id=usuario_cliente.pk, estado_id="pagado")
    p_pend = Pedido.objects.create(cliente_id=usuario_cliente.pk, estado_id="pendiente")
    pago_pagado = Pago.objects.create(
        pedido_id=p_pagado.pk, monto=Decimal("50.00"), estado_id="aprobado", referencia="OK1"
    )
    Venta.objects.create(pedido_id=p_pagado.pk, total=Decimal("50.00"))
    pago_pend = Pago.objects.create(
        pedido_id=p_pend.pk, monto=Decimal("15.00"), estado_id="pendiente", referencia=""
    )

    _migrate(DESPUES)

    # Revertir (debe pasar: 1 intento por pedido).
    _migrate(ANTES)
    apps_v = _apps_at(ANTES)
    PedidoV = apps_v.get_model("pedidos", "Pedido")
    PagoV = apps_v.get_model("pagos", "Pago")
    VentaV = apps_v.get_model("pagos", "Venta")

    assert PedidoV.objects.get(pk=p_pagado.pk).estado_id == "pagado"
    assert PedidoV.objects.get(pk=p_pend.pk).estado_id == "pendiente"
    assert PagoV.objects.get(pk=pago_pagado.pk).monto == Decimal("50.00")
    assert PagoV.objects.get(pk=pago_pagado.pk).estado_id == "aprobado"
    # referencia LEGACY generada en forward debe restaurarse a vacía en reverso de backfill.
    assert PagoV.objects.get(pk=pago_pend.pk).referencia == ""
    assert VentaV.objects.get(pedido_id=p_pagado.pk).total == Decimal("50.00")

    _migrate()


@pytest.mark.django_db(transaction=True)
def test_reversion_aborta_si_varios_intentos_por_pedido(usuario_cliente):
    """La reversión OneToOne←FK aborta con RuntimeError claro si >1 intento/pedido."""
    _migrate(ANTES)
    apps = _apps_at(ANTES)
    Pedido = apps.get_model("pedidos", "Pedido")
    Pago = apps.get_model("pagos", "Pago")

    p = Pedido.objects.create(cliente_id=usuario_cliente.pk, estado_id="pendiente")
    Pago.objects.create(pedido_id=p.pk, monto=Decimal("10.00"), estado_id="rechazado", referencia="R1")
    # Un solo pago por pedido en esquema anterior (OneToOne). Crear segundo solo es
    # posible tras migrar a FK; así que migramos adelante y añadimos otro intento.
    _migrate(DESPUES)

    from pagos.models import IntentoPago
    IntentoPago.objects.create(
        pedido_id=p.pk,
        importe=Decimal("10.00"),
        estado_id="pendiente",
        referencia="R2-extra",
        clave_idempotencia="",
    )
    assert IntentoPago.objects.filter(pedido_id=p.pk).count() == 2

    with pytest.raises(RuntimeError) as excinfo:
        _migrate(ANTES)

    msg = str(excinfo.value)
    assert "pagos_intentopago" in msg
    assert "pedido_id" in msg
    assert "más de un intento" in msg

    # Limpieza: eliminar intento extra y restaurar hojas.
    _migrate(DESPUES)
    from pagos.models import IntentoPago as IP
    IP.objects.filter(pedido_id=p.pk, referencia="R2-extra").delete()
    _migrate()
