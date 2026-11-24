"""
Pruebas de las migraciones de integridad (AZ-S1-15):

  - Desde el esquema anterior: los datos válidos se conservan y los nuevos
    ``CheckConstraint`` quedan activos al avanzar la cadena.
  - Ante datos inválidos preexistentes, la migración de datos ABORTA con un
    mensaje que indica tabla, campo y cantidad de filas afectadas, sin
    normalizar nada en silencio.
"""
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from pagos.models import IntentoPago, Venta
from pedidos.models import DetallePedido, Pedido

# Esquema inmediatamente anterior a los checks de AZ-S1-15.
ANTES_DE_CHECKS_PEDIDOS = [
    ("catalogo", "0003_indices_catalogo"),
    ("pedidos", "0002_detallepedido_oferta"),
    ("pagos", "0001_initial"),
]

# Pedidos ya con checks, pagos todavía sin ellos.
ANTES_DE_CHECKS_PAGOS = [
    ("catalogo", "0003_indices_catalogo"),
    ("pedidos", "0003_integridad_detallepedido"),
    ("pagos", "0001_initial"),
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


# ── Avance desde el esquema anterior ─────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
def test_migracion_pedidos_conserva_datos_validos_y_activa_checks(
    usuario_cliente, oferta
):
    """Los detalles válidos sobreviven y el check de cantidad queda activo."""
    _migrate(ANTES_DE_CHECKS_PEDIDOS)
    apps_viejo = _apps_at(ANTES_DE_CHECKS_PEDIDOS)
    PedidoViejo = apps_viejo.get_model("pedidos", "Pedido")
    DetalleViejo = apps_viejo.get_model("pedidos", "DetallePedido")

    pedido_viejo = PedidoViejo.objects.create(
        cliente_id=usuario_cliente.pk, estado="pendiente"
    )
    DetalleViejo.objects.create(
        pedido=pedido_viejo,
        oferta_id=oferta.pk,
        cantidad=2,
        precio_unitario=Decimal("10.00"),
    )

    _migrate()

    detalle = DetallePedido.objects.get(pedido_id=pedido_viejo.pk)
    assert detalle.cantidad == 2
    assert detalle.precio_unitario == Decimal("10.00")

    pedido_nuevo = Pedido.objects.create(cliente=usuario_cliente)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DetallePedido.objects.create(
                pedido=pedido_nuevo,
                oferta=oferta,
                cantidad=0,
                precio_unitario=Decimal("10.00"),
            )


@pytest.mark.django_db(transaction=True)
def test_migracion_pagos_conserva_datos_validos_y_activa_checks(
    pedido_con_item,
):
    """Pagos y ventas válidos sobreviven y los checks de importe quedan activos."""
    _migrate(ANTES_DE_CHECKS_PAGOS)
    apps_viejo = _apps_at(ANTES_DE_CHECKS_PAGOS)
    PagoViejo = apps_viejo.get_model("pagos", "Pago")
    VentaVieja = apps_viejo.get_model("pagos", "Venta")

    PagoViejo.objects.create(
        pedido_id=pedido_con_item.pk,
        monto=Decimal("150.00"),
        estado="aprobado",
    )
    VentaVieja.objects.create(
        pedido_id=pedido_con_item.pk,
        total=Decimal("150.00"),
    )

    _migrate()

    intento = IntentoPago.objects.get(pedido=pedido_con_item)
    assert intento.importe == Decimal("150.00")
    venta = Venta.objects.get(pedido=pedido_con_item)
    assert venta.total == Decimal("150.00")
    assert venta.intento_aprobado_id == intento.pk

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IntentoPago.objects.filter(pk=intento.pk).update(
                importe=Decimal("-1.00")
            )


# ── Aborto ante datos inválidos preexistentes ────────────────────────────────

def _crear_detalle_historico(usuario_cliente, oferta, apps_viejo, **valores):
    PedidoViejo = apps_viejo.get_model("pedidos", "Pedido")
    DetalleViejo = apps_viejo.get_model("pedidos", "DetallePedido")
    pedido = PedidoViejo.objects.create(
        cliente_id=usuario_cliente.pk, estado="pendiente"
    )
    return DetalleViejo.objects.create(
        pedido=pedido,
        oferta_id=oferta.pk,
        cantidad=valores.get("cantidad", 1),
        precio_unitario=valores.get("precio_unitario", Decimal("10.00")),
    )


@pytest.mark.django_db(transaction=True)
def test_migracion_aborta_si_hay_cantidad_menor_a_uno(usuario_cliente, oferta):
    _migrate(ANTES_DE_CHECKS_PEDIDOS)
    apps_viejo = _apps_at(ANTES_DE_CHECKS_PEDIDOS)
    detalle = _crear_detalle_historico(
        usuario_cliente, oferta, apps_viejo, cantidad=0
    )

    with pytest.raises(RuntimeError) as error:
        _migrate()

    mensaje = str(error.value)
    assert "pedidos_detallepedido" in mensaje
    assert "cantidad" in mensaje
    assert "1 fila" in mensaje

    # Restauración: corregir/eliminar el dato inválido y volver al último estado.
    detalle.delete()
    _migrate()


@pytest.mark.django_db(transaction=True)
def test_migracion_aborta_si_hay_precio_unitario_negativo(usuario_cliente, oferta):
    _migrate(ANTES_DE_CHECKS_PEDIDOS)
    apps_viejo = _apps_at(ANTES_DE_CHECKS_PEDIDOS)
    detalle = _crear_detalle_historico(
        usuario_cliente,
        oferta,
        apps_viejo,
        precio_unitario=Decimal("-5.00"),
    )

    with pytest.raises(RuntimeError) as error:
        _migrate()

    mensaje = str(error.value)
    assert "pedidos_detallepedido" in mensaje
    assert "precio_unitario" in mensaje
    assert "1 fila" in mensaje

    detalle.delete()
    _migrate()


@pytest.mark.django_db(transaction=True)
def test_migracion_aborta_si_hay_monto_negativo(pedido_con_item):
    _migrate(ANTES_DE_CHECKS_PAGOS)
    apps_viejo = _apps_at(ANTES_DE_CHECKS_PAGOS)
    PagoViejo = apps_viejo.get_model("pagos", "Pago")
    pago = PagoViejo.objects.create(
        pedido_id=pedido_con_item.pk,
        monto=Decimal("-20.00"),
        estado="pendiente",
    )

    with pytest.raises(RuntimeError) as error:
        _migrate()

    mensaje = str(error.value)
    assert "pagos_pago" in mensaje
    assert "monto" in mensaje
    assert "1 fila" in mensaje

    pago.delete()
    _migrate()


@pytest.mark.django_db(transaction=True)
def test_migracion_aborta_si_hay_total_negativo(pedido_con_item):
    _migrate(ANTES_DE_CHECKS_PAGOS)
    apps_viejo = _apps_at(ANTES_DE_CHECKS_PAGOS)
    VentaVieja = apps_viejo.get_model("pagos", "Venta")
    venta = VentaVieja.objects.create(
        pedido_id=pedido_con_item.pk,
        total=Decimal("-20.00"),
    )

    with pytest.raises(RuntimeError) as error:
        _migrate()

    mensaje = str(error.value)
    assert "pagos_venta" in mensaje
    assert "total" in mensaje
    assert "1 fila" in mensaje

    venta.delete()
    _migrate()
