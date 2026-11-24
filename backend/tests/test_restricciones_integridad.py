"""
Pruebas de las restricciones SQL de integridad (AZ-S1-15).

Cada prueba intenta escribir directamente con el ORM (sin ``full_clean``):
la base de datos debe rechazar la fila con ``IntegrityError``. Se usa
``transaction.atomic()`` para aislar la escritura fallida y que la conexión
de la prueba quede utilizable.
"""
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction

from pagos.models import IntentoPago, Venta
from pedidos.models import DetallePedido, Pedido


def _pedido(usuario_cliente):
    return Pedido.objects.create(
        cliente=usuario_cliente, estado_id="pendiente"
    )


# ── DetallePedido ────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_detalle_cantidad_cero_es_rechazada(usuario_cliente, oferta):
    """``pedidos_detallepedido_cantidad_positiva``: cantidad >= 1."""
    pedido = _pedido(usuario_cliente)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DetallePedido.objects.create(
                pedido=pedido,
                oferta=oferta,
                cantidad=0,
                precio_unitario=Decimal("10.00"),
            )


@pytest.mark.django_db
def test_detalle_precio_unitario_negativo_es_rechazado(usuario_cliente, oferta):
    """``pedidos_detallepedido_precio_unitario_no_negativo``: precio >= 0."""
    pedido = _pedido(usuario_cliente)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DetallePedido.objects.create(
                pedido=pedido,
                oferta=oferta,
                cantidad=1,
                precio_unitario=Decimal("-0.01"),
            )


@pytest.mark.django_db
def test_detalle_acepta_los_limites_inferiores(usuario_cliente, oferta):
    """Los bordes permitidos (cantidad 1, precio 0) sí se persisten."""
    pedido = _pedido(usuario_cliente)

    with transaction.atomic():
        detalle = DetallePedido.objects.create(
            pedido=pedido,
            oferta=oferta,
            cantidad=1,
            precio_unitario=Decimal("0.00"),
        )

    detalle.refresh_from_db()
    assert detalle.cantidad == 1
    assert detalle.precio_unitario == Decimal("0.00")


# ── Intento de pago ──────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_intento_importe_negativo_es_rechazado(pedido_con_item):
    """``pagos_intento_importe_nn``: importe >= 0."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IntentoPago.objects.create(
                pedido=pedido_con_item,
                importe=Decimal("-100.00"),
                estado_id="pendiente",
                referencia="REF-INT-NEG",
            )


@pytest.mark.django_db
def test_intento_importe_cero_es_valido(pedido_con_item):
    with transaction.atomic():
        intento = IntentoPago.objects.create(
            pedido=pedido_con_item,
            importe=Decimal("0.00"),
            estado_id="pendiente",
            referencia="REF-INT-CERO",
        )

    assert intento.pk is not None


# ── Venta ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_venta_total_negativo_es_rechazado(pedido_con_item):
    """``pagos_venta_total_no_negativo``: total >= 0."""
    intento = IntentoPago.objects.create(
        pedido=pedido_con_item,
        importe=pedido_con_item.total,
        estado_id="aprobado",
        referencia="REF-VTA-NEG",
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Venta.objects.create(
                pedido=pedido_con_item,
                intento_aprobado=intento,
                total=Decimal("-0.01"),
            )


@pytest.mark.django_db
def test_venta_total_cero_es_valido(pedido_con_item):
    intento = IntentoPago.objects.create(
        pedido=pedido_con_item,
        importe=Decimal("0.00"),
        estado_id="aprobado",
        referencia="REF-VTA-CERO",
    )
    with transaction.atomic():
        venta = Venta.objects.create(
            pedido=pedido_con_item,
            intento_aprobado=intento,
            total=Decimal("0.00"),
        )

    assert venta.pk is not None


# ── Índices nuevos ───────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_indices_nuevos_existen_en_la_base_de_datos():
    """Las migraciones crean los índices de consulta planificados (AZ-S1-15/16)."""
    esperados = {
        "catalogo_ofertavideojuego": {
            "catalogo_oferta_est_stock_idx",
            "catalogo_oferta_plat_est_idx",
        },
        # Las tablas puente sustituyen los índices de Videojuego(categoria|genero, activo),
        # que dejan de existir al retirar las FKs directas.
        "catalogo_videojuegocategoria": {"catalogo_vjc_categoria_idx"},
        "catalogo_videojuegogenero": {"catalogo_vjg_genero_idx"},
        "pedidos_pedido": {"pedidos_pedido_cli_fecha_idx"},
        "pagos_venta": {"pagos_venta_registrada_idx"},
        "pagos_intentopago": {
            "pagos_intento_ped_fec_idx",
            "pagos_intento_est_fec_idx",
        },
        "pedidos_historialestadopedido": {"pedidos_hist_ped_fec_idx"},
    }

    with connection.cursor() as cursor:
        for tabla, nombres in esperados.items():
            indices = connection.introspection.get_constraints(cursor, tabla)
            assert nombres <= set(indices), (
                f"Faltan índices en {tabla}: {nombres - set(indices)}"
            )

        indices_videojuego = set(
            connection.introspection.get_constraints(cursor, "catalogo_videojuego")
        )
        obsoletos = {
            "catalogo_vj_cat_activo_idx",
            "catalogo_vj_gen_activo_idx",
        }
        assert not (obsoletos & indices_videojuego), (
            f"Los índices de AZ-S1-15 deben retirarse: {obsoletos & indices_videojuego}"
        )
