"""
Pruebas del ciclo transaccional normalizado (AZ-S1-19).

Cubre: intentos 1:N, unicidad/referencia e idempotencia, importe, FKs y PROTECT,
venta 1:1 vinculada al intento aprobado, historial inmutable y snapshots.
"""
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError

from catalogo.models import OfertaVideojuego
from inventario.models import RegistroInmutableError
from pagos.models import EstadoIntentoPago, IntentoPago, Venta
from pedidos.models import EstadoPedido, HistorialEstadoPedido, Pedido


def _crear_intento(pedido, *, estado="pendiente", importe=None, referencia, clave=""):
    return IntentoPago.objects.create(
        pedido=pedido,
        importe=pedido.total if importe is None else importe,
        estado_id=estado,
        referencia=referencia,
        clave_idempotencia=clave,
    )


# ── Intentos de pago (1:N) ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_un_pedido_permite_varios_intentos_con_distintos_estados(pedido_con_item):
    """Un pedido puede tener múltiples intentos (p. ej. tras un rechazo)."""
    i1 = _crear_intento(pedido_con_item, estado="rechazado", referencia="REF-A-1")
    i2 = _crear_intento(pedido_con_item, estado="pendiente", referencia="REF-A-2")
    i3 = _crear_intento(pedido_con_item, estado="aprobado", referencia="REF-A-3")

    assert pedido_con_item.intentos_pago.count() == 3
    assert {i.estado_id for i in [i1, i2, i3]} == {"rechazado", "pendiente", "aprobado"}


@pytest.mark.django_db
def test_referencia_duplicada_rechazada(pedido_con_item):
    _crear_intento(pedido_con_item, referencia="REF-DUP")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _crear_intento(pedido_con_item, referencia="REF-DUP")


@pytest.mark.django_db
def test_clave_idempotencia_duplicada_rechazada_y_vacia_permitida(pedido_con_item):
    _crear_intento(pedido_con_item, referencia="REF-I-1", clave="idem-123")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _crear_intento(pedido_con_item, referencia="REF-I-2", clave="idem-123")

    # Vacía se permite múltiples veces (unicidad condicional).
    _crear_intento(pedido_con_item, referencia="REF-I-3", clave="")
    _crear_intento(pedido_con_item, referencia="REF-I-4", clave="")
    assert pedido_con_item.intentos_pago.filter(clave_idempotencia="").count() == 2


@pytest.mark.django_db
def test_importe_negativo_rechazado(pedido_con_item):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _crear_intento(
                pedido_con_item,
                importe=Decimal("-1.00"),
                referencia="REF-IMP-NEG",
            )


@pytest.mark.django_db
def test_intento_rechaza_fk_inexistente(pedido_con_item, usuario_cliente):
    # Pedido inexistente.
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IntentoPago.objects.create(
                pedido_id=999999,
                importe=Decimal("10.00"),
                estado_id="pendiente",
                referencia="REF-FK-PED",
            )
            connection.check_constraints()

    # Estado inexistente.
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IntentoPago.objects.create(
                pedido=pedido_con_item,
                importe=Decimal("10.00"),
                estado_id="no_existe",
                referencia="REF-FK-EST",
            )
            connection.check_constraints()


@pytest.mark.django_db
def test_protect_en_pedido_estado_y_actor_de_intento(pedido_con_item, usuario_cliente):
    intento = _crear_intento(pedido_con_item, estado="aprobado", referencia="REF-PROT")
    estado = EstadoIntentoPago.objects.get(codigo="aprobado")

    with pytest.raises(ProtectedError):
        estado.delete()
    with pytest.raises(ProtectedError):
        pedido_con_item.delete()
    with pytest.raises(ProtectedError):
        usuario_cliente.delete()

    assert IntentoPago.objects.filter(pk=intento.pk).exists()


# ── Venta ─────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_solo_una_venta_por_pedido(pedido_con_item):
    intento = _crear_intento(pedido_con_item, estado="aprobado", referencia="REF-V-1")
    Venta.objects.create(
        pedido=pedido_con_item, intento_aprobado=intento, total=pedido_con_item.total
    )
    intento2 = _crear_intento(pedido_con_item, estado="aprobado", referencia="REF-V-2")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Venta.objects.create(
                pedido=pedido_con_item,
                intento_aprobado=intento2,
                total=pedido_con_item.total,
            )


@pytest.mark.django_db
def test_un_intento_origina_como_maximo_una_venta(pedido_con_item, usuario_cliente):
    intento = _crear_intento(pedido_con_item, estado="aprobado", referencia="REF-V-INT1")
    Venta.objects.create(
        pedido=pedido_con_item, intento_aprobado=intento, total=pedido_con_item.total
    )
    otro_pedido = Pedido.objects.create(cliente=usuario_cliente, estado_id="pendiente")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Venta.objects.create(
                pedido=otro_pedido,
                intento_aprobado=intento,
                total=Decimal("0.00"),
            )


@pytest.mark.django_db
def test_intento_aprobado_protegido_por_venta(pedido_con_item):
    intento = _crear_intento(pedido_con_item, estado="aprobado", referencia="REF-V-PROT")
    Venta.objects.create(
        pedido=pedido_con_item, intento_aprobado=intento, total=pedido_con_item.total
    )
    with pytest.raises(ProtectedError):
        intento.delete()


# ── Historial de estados de pedido ────────────────────────────────────────────


@pytest.mark.django_db
def test_historial_conserva_transiciones_y_es_inmutable(pedido_con_item, usuario_cliente):
    h1 = HistorialEstadoPedido.objects.create(
        pedido=pedido_con_item,
        estado_id="pendiente",
        actor=usuario_cliente,
        observacion="Creado",
    )
    h2 = HistorialEstadoPedido.objects.create(
        pedido=pedido_con_item,
        estado_id="pagado",
        actor=usuario_cliente,
        observacion="Pagado",
    )

    assert list(
        pedido_con_item.historial_estados.order_by("pk").values_list("estado_id", flat=True)
    ) == ["pendiente", "pagado"]

    # update bloqueado
    with pytest.raises(RegistroInmutableError):
        HistorialEstadoPedido.objects.filter(pk=h1.pk).update(observacion="x")
    # delete instancia bloqueado
    with pytest.raises(RegistroInmutableError):
        h1.delete()
    # delete masivo bloqueado
    with pytest.raises(RegistroInmutableError):
        HistorialEstadoPedido.objects.filter(pedido=pedido_con_item).delete()

    assert HistorialEstadoPedido.objects.filter(pk__in=[h1.pk, h2.pk]).count() == 2


@pytest.mark.django_db
def test_pedido_con_historial_no_se_puede_borrar(pedido_con_item):
    HistorialEstadoPedido.objects.create(
        pedido=pedido_con_item, estado_id="pendiente", observacion="Inicial"
    )
    with pytest.raises(ProtectedError):
        pedido_con_item.delete()


# ── Inmutabilidad de importes históricos / snapshots ─────────────────────────


@pytest.mark.django_db
def test_importes_historicos_no_cambian_al_modificar_precio_vigente(pedido_con_item, oferta):
    """Cambiar OfertaVideojuego.precio_vigente no altera snapshots ya registrados."""
    detalle = pedido_con_item.detalles.first()
    intento = _crear_intento(pedido_con_item, estado="aprobado", referencia="REF-SNAP")
    venta = Venta.objects.create(
        pedido=pedido_con_item, intento_aprobado=intento, total=pedido_con_item.total
    )

    precio_unitario_original = detalle.precio_unitario
    subtotal_original = detalle.subtotal
    total_original = venta.total

    OfertaVideojuego.objects.filter(pk=oferta.pk).update(precio_vigente=Decimal("999999.99"))

    detalle.refresh_from_db()
    venta.refresh_from_db()
    assert detalle.precio_unitario == precio_unitario_original
    assert detalle.subtotal == subtotal_original
    assert venta.total == total_original


# ── Propiedad de compatibilidad ───────────────────────────────────────────────


@pytest.mark.django_db
def test_propiedad_pedido_pago_devuelve_intento_aprobado(pedido_con_item):
    assert pedido_con_item.pago is None
    _crear_intento(pedido_con_item, estado="rechazado", referencia="REF-C-1")
    assert pedido_con_item.pago is None
    aprobado = _crear_intento(pedido_con_item, estado="aprobado", referencia="REF-C-2")
    assert pedido_con_item.pago.pk == aprobado.pk


# ── Sin datos sensibles ──────────────────────────────────────────────────────


@pytest.mark.django_db
def test_modelos_pedidos_pagos_sin_campos_sensibles():
    """Ningún modelo de pedidos/pagos define campos de datos sensibles de tarjeta."""
    prohibidos = ("tarjeta", "card", "cvv", "pan", "cvc")
    from django.apps import apps as django_apps

    for app_label in ("pedidos", "pagos"):
        for model in django_apps.get_app_config(app_label).get_models():
            nombres = [f.name.lower() for f in model._meta.get_fields()]
            for nombre in nombres:
                for token in prohibidos:
                    assert token not in nombre, (
                        f"Campo sensible '{nombre}' (contiene '{token}') "
                        f"en {model._meta.label}"
                    )
