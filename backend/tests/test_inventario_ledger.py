"""
Pruebas del libro mayor de movimientos de inventario (AZ-S1-14):
  - Catálogos relacionales con codigo único y semilla idempotente.
  - Invariantes del ledger: cantidad positiva, saldos no negativos,
    idempotencia por clave única y unicidad condicional del detalle.
  - Inmutabilidad: ni instancia ni queryset pueden mutar la historia.
  - Trazabilidad: una salida por venta llega hasta su detalle de pedido.
  - Historial consultable por oferta (y uso real de los índices).
  - Concurrencia: idempotencia y saldo no negativo bajo hilos.
"""
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone as dt_timezone
from importlib import import_module

import pytest
from django.apps import apps as apps_reales
from django.db import (
    IntegrityError,
    OperationalError,
    connection,
    transaction,
)
from django.db.models.deletion import ProtectedError

from catalogo.models import OfertaVideojuego
from cuentas.models import Usuario
from inventario.models import (
    MotivoMovimientoInventario,
    MovimientoInventarioOfertaVideojuego,
    RegistroInmutableError,
    TipoMovimientoInventario,
)

# Alias de legibilidad para el modelo del ledger.
Movimiento = MovimientoInventarioOfertaVideojuego


def _movimiento(oferta, tipo_movimiento, **overrides):
    """Crea un movimiento válido; los overrides fuerzan cada caso de prueba."""
    valores = {
        "oferta": oferta,
        "tipo_movimiento": tipo_movimiento,
        "cantidad": 1,
        "saldo_anterior": 10,
        "saldo_posterior": 9,
        "clave_idempotencia": f"test-{uuid.uuid4()}",
    }
    valores.update(overrides)
    return Movimiento.objects.create(**valores)


# ── Catálogos: unicidad de codigo y semilla idempotente ───────────────────────


@pytest.mark.django_db
def test_codigo_de_tipo_de_movimiento_es_unico(tipo_entrada):
    """No pueden existir dos tipos con el mismo codigo estable."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TipoMovimientoInventario.objects.create(
                codigo="ENTRADA", nombre="Otra entrada", naturaleza="entrada"
            )


@pytest.mark.django_db
def test_codigo_de_motivo_es_unico(motivo_venta):
    """No pueden existir dos motivos con el mismo codigo estable."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            MotivoMovimientoInventario.objects.create(
                codigo="VENTA", nombre="Otra venta"
            )


@pytest.mark.django_db
def test_la_semilla_de_catalogos_es_idempotente():
    """La data migration 0002 puede reejecutarse sin duplicar filas."""
    from django.db.migrations.recorder import MigrationRecorder

    # La semilla quedó registrada como migración aplicada.
    assert MigrationRecorder.Migration.objects.filter(
        app="inventario", name="0002_semilla_tipos_motivos"
    ).exists()

    semilla = import_module("inventario.migrations.0002_semilla_tipos_motivos")
    semilla.sembrar_catalogos(apps_reales, None)
    semilla.sembrar_catalogos(apps_reales, None)

    tipos = TipoMovimientoInventario.objects.filter(
        codigo__in=["ENTRADA", "SALIDA", "AJUSTE"]
    )
    motivos = MotivoMovimientoInventario.objects.filter(
        codigo__in=["VENTA", "DEVOLUCION", "AJUSTE_FISICO", "CARGA_INICIAL"]
    )
    assert tipos.count() == 3
    assert motivos.count() == 4
    assert {t.naturaleza for t in tipos} == {"entrada", "salida", "ajuste"}


# ── Invariantes del ledger ────────────────────────────────────────────────────


@pytest.mark.django_db
def test_cantidad_cero_es_rechazada(oferta, tipo_salida):
    """La cantidad operada es estrictamente positiva."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _movimiento(oferta, tipo_salida, cantidad=0, saldo_posterior=10)


@pytest.mark.django_db
def test_cantidad_negativa_es_rechazada(oferta, tipo_salida):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _movimiento(oferta, tipo_salida, cantidad=-3)


@pytest.mark.django_db
def test_saldo_anterior_negativo_es_rechazado(oferta, tipo_salida):
    """El saldo corrido nunca es negativo, ni antes ni después."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _movimiento(oferta, tipo_salida, saldo_anterior=-1, saldo_posterior=0)


@pytest.mark.django_db
def test_saldo_posterior_negativo_es_rechazado(oferta, tipo_salida):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _movimiento(oferta, tipo_salida, saldo_anterior=5, saldo_posterior=-2)


@pytest.mark.django_db
def test_la_clave_de_idempotencia_es_unica(movimiento_entrada, oferta, tipo_salida):
    """Un reintento con la misma clave no puede duplicar el movimiento."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _movimiento(
                oferta, tipo_salida,
                clave_idempotencia=movimiento_entrada.clave_idempotencia,
            )


@pytest.mark.django_db
def test_el_detalle_de_pedido_se_referencia_una_sola_vez(
    pedido_con_item, oferta, tipo_salida
):
    """Trazabilidad 1:1 entre movimiento de venta y detalle de pedido."""
    detalle = pedido_con_item.detalles.first()
    _movimiento(oferta, tipo_salida, detalle_pedido=detalle)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            _movimiento(oferta, tipo_salida, detalle_pedido=detalle)


@pytest.mark.django_db
def test_movimientos_sin_detalle_de_pedido_admiten_null_repetido(
    oferta, tipo_salida
):
    """Los movimientos de sistema (detalle null) no chocan entre sí."""
    _movimiento(oferta, tipo_salida)
    _movimiento(oferta, tipo_salida)
    assert Movimiento.objects.count() == 2


@pytest.mark.django_db
def test_fecha_hora_se_registra_automaticamente(movimiento_entrada):
    """El registro autogenera su marca temporal y la autoría es opcional."""
    assert movimiento_entrada.fecha_hora is not None
    assert movimiento_entrada.usuario_responsable is None  # proceso del sistema


# ── Inmutabilidad ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_un_movimiento_existente_no_se_puede_modificar(movimiento_entrada):
    """La historia del ledger no se reescribe: solo se inserta."""
    movimiento_entrada.observacion = "intento de edición"
    with pytest.raises(RegistroInmutableError):
        movimiento_entrada.save()
    movimiento_entrada.refresh_from_db()
    assert movimiento_entrada.observacion == ""


@pytest.mark.django_db
def test_un_movimiento_no_se_puede_eliminar(movimiento_entrada):
    with pytest.raises(RegistroInmutableError):
        movimiento_entrada.delete()


@pytest.mark.django_db
def test_un_queryset_no_puede_actualizar_el_ledger(movimiento_entrada):
    with pytest.raises(RegistroInmutableError):
        Movimiento.objects.filter(pk=movimiento_entrada.pk).update(
            observacion="edición en lote"
        )


@pytest.mark.django_db
def test_un_queryset_no_puede_eliminar_del_ledger(movimiento_entrada):
    with pytest.raises(RegistroInmutableError):
        Movimiento.objects.filter(pk=movimiento_entrada.pk).delete()


@pytest.mark.django_db
def test_bulk_update_no_puede_reescribir_el_ledger(movimiento_entrada):
    movimiento_entrada.observacion = "solo en memoria"
    with pytest.raises(RegistroInmutableError):
        Movimiento.objects.bulk_update([movimiento_entrada], ["observacion"])


@pytest.mark.django_db
def test_el_manager_relacionado_tambien_es_inmutable(movimiento_entrada):
    """oferta.movimientos_inventario hereda el contrato inmutable."""
    with pytest.raises(RegistroInmutableError):
        movimiento_entrada.oferta.movimientos_inventario.update(
            observacion="vía relación"
        )
    with pytest.raises(RegistroInmutableError):
        movimiento_entrada.oferta.movimientos_inventario.delete()


# ── Integridad referencial y trazabilidad ─────────────────────────────────────


@pytest.mark.django_db
def test_no_se_puede_borrar_la_oferta_con_movimientos(movimiento_entrada):
    with pytest.raises(ProtectedError):
        movimiento_entrada.oferta.delete()


@pytest.mark.django_db
def test_no_se_puede_borrar_el_tipo_con_movimientos(movimiento_entrada):
    with pytest.raises(ProtectedError):
        movimiento_entrada.tipo_movimiento.delete()


@pytest.mark.django_db
def test_no_se_puede_borrar_el_usuario_autor_de_un_movimiento(
    oferta, tipo_salida, usuario_cliente
):
    """La autoría histórica queda protegida (PROTECT: auditar es no borrar)."""
    _movimiento(oferta, tipo_salida, usuario_responsable=usuario_cliente)
    with pytest.raises(ProtectedError):
        Usuario.objects.get(pk=usuario_cliente.pk).delete()


@pytest.mark.django_db
def test_no_se_puede_borrar_el_pedido_origen_del_movimiento(
    pedido_con_item, oferta, tipo_salida
):
    """El detalle que originó una salida queda protegido contra CASCADE."""
    detalle = pedido_con_item.detalles.first()
    _movimiento(oferta, tipo_salida, detalle_pedido=detalle)

    with pytest.raises(ProtectedError):
        pedido_con_item.delete()


@pytest.mark.django_db
def test_salida_por_venta_es_rastreable_hasta_su_detalle(
    pedido_con_item, oferta, tipo_salida, motivo_venta, usuario_cliente
):
    """La referencia única conecta la salida con su operación de venta."""
    detalle = pedido_con_item.detalles.first()
    movimiento = _movimiento(
        oferta, tipo_salida,
        motivo=motivo_venta,
        usuario_responsable=usuario_cliente,
        detalle_pedido=detalle,
    )

    assert movimiento.detalle_pedido == detalle
    assert movimiento.detalle_pedido.pedido_id == pedido_con_item.pk
    # La FK es condicionalmente única (null permitido): el reverso es un
    # manager que resuelve al único movimiento cuando existe.
    assert detalle.movimiento_inventario.get() == movimiento


@pytest.mark.django_db
def test_las_correcciones_son_movimientos_compensatorios(
    movimiento_entrada, oferta, tipo_salida
):
    """Una corrección es un movimiento nuevo que referencia al original."""
    compensatorio = _movimiento(
        oferta, tipo_salida,
        cantidad=5,
        saldo_anterior=15,
        saldo_posterior=10,
        movimiento_compensado=movimiento_entrada,
        observacion="Reversa del movimiento original",
    )

    assert movimiento_entrada.movimientos_compensatorios.get() == compensatorio
    assert compensatorio.movimiento_compensado == movimiento_entrada


# ── Historial por oferta ───────────────────────────────────────────────────────


@pytest.mark.django_db
def test_historial_de_una_oferta_por_tipo_y_fecha(
    videojuego, plataforma_alternativa, oferta,
    tipo_entrada, tipo_salida, tipo_ajuste,
):
    """Entradas, salidas y ajustes de la oferta, ordenadas por fecha."""
    otra = OfertaVideojuego.objects.create(
        videojuego=videojuego,
        plataforma=plataforma_alternativa,
        precio_vigente=1,
        stock=99,
        sku="AZ-HIST-002",
    )
    base = datetime(2026, 1, 1, 12, 0, tzinfo=dt_timezone.utc)

    _movimiento(oferta, tipo_entrada, cantidad=6,
                saldo_anterior=10, saldo_posterior=16,
                fecha_hora=base)
    _movimiento(oferta, tipo_salida, cantidad=2,
                saldo_anterior=16, saldo_posterior=14,
                fecha_hora=base + timedelta(hours=1))
    _movimiento(oferta, tipo_ajuste, cantidad=12,
                saldo_anterior=14, saldo_posterior=12,
                fecha_hora=base + timedelta(hours=2))
    _movimiento(otra, tipo_entrada, fecha_hora=base)  # ruido: otra oferta

    historial = oferta.movimientos_inventario.order_by("fecha_hora")
    assert [m.tipo_movimiento.codigo for m in historial] == [
        "ENTRADA", "SALIDA", "AJUSTE",
    ]
    salidas = oferta.movimientos_inventario.filter(
        tipo_movimiento__codigo="SALIDA"
    )
    assert salidas.count() == 1
    assert salidas.get().saldo_posterior == 14


def _plan_de_consulta(consulta):
    """Devuelve el plan de ejecución de SQLite para una consulta del ORM."""
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN QUERY PLAN " + str(consulta.query))
        return " ".join(str(fila[3]) for fila in cursor.fetchall())


@pytest.mark.django_db
def test_el_historial_por_oferta_usa_el_indice_compuesto(oferta, tipo_salida):
    """(oferta, -fecha_hora) resuelve el historial sin escanear la tabla."""
    _movimiento(oferta, tipo_salida)
    consulta = Movimiento.objects.filter(oferta=oferta).order_by("-fecha_hora")
    assert "inventario_oferta_fecha_idx" in _plan_de_consulta(consulta)


@pytest.mark.django_db
def test_el_historial_por_tipo_usa_el_indice_compuesto(oferta, tipo_salida):
    """(tipo_movimiento, -fecha_hora) resuelve consultas por tipo y fecha."""
    _movimiento(oferta, tipo_salida)
    consulta = Movimiento.objects.filter(tipo_movimiento=tipo_salida).order_by(
        "-fecha_hora"
    )
    assert "inventario_mov_tipo_fecha_idx" in _plan_de_consulta(consulta)


# ── Concurrencia ───────────────────────────────────────────────────────────────


def _con_reintentos_de_lock(operacion, intentos=50, pausa=0.01):
    """
    Ejecuta la operación reintentando SOLO los locks del harness de pruebas.

    La BD de pruebas es SQLite en memoria compartida entre hilos: cuando un
    hilo pierde la carrera por el lock de escritura, su ``BEGIN IMMEDIATE``
    falla con SQLITE_LOCKED ("database table is locked"), que el busy
    handler del driver no reintenta. Es un artefacto del harness — en
    PostgreSQL el perdedor bloquearía en el INSERT y recibiría el
    IntegrityError del constraint — así que se reintenta el bloque completo
    hasta que el hilo completa su transacción o la BD rechaza la operación.

    El bloque es reiniciable por diseño: ``transaction.atomic()`` garantiza
    que un intento fallido no deja estado parcial. Los errores de datos
    (IntegrityError y cualquier otro) se propagan de inmediato.
    """
    ultimo = None
    for _ in range(intentos):
        try:
            return operacion()
        except OperationalError as error:
            if "locked" not in str(error).lower():
                raise
            ultimo = error
            time.sleep(pausa)
    raise AssertionError(
        f"El harness no cedió el lock de escritura tras {intentos} intentos: {ultimo}"
    )


@pytest.mark.django_db(transaction=True)
def test_concurrencia_la_clave_de_idempotencia_deja_un_solo_movimiento(
    oferta, tipo_salida
):
    """Dos hilos con la misma clave: la BD solo acepta uno."""
    clave = f"idem-{uuid.uuid4()}"

    def registrar():
        with transaction.atomic():
            _movimiento(oferta, tipo_salida, clave_idempotencia=clave)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futuros = [pool.submit(_con_reintentos_de_lock, registrar) for _ in range(2)]
        excepciones = [f.exception() for f in futuros]

    rechazados = [e for e in excepciones if e is not None]
    assert len(rechazados) == 1
    assert isinstance(rechazados[0], IntegrityError)
    assert Movimiento.objects.filter(clave_idempotencia=clave).count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrencia_el_saldo_no_queda_negativo(oferta, tipo_salida):
    """
    Dos salidas simultáneas de 8 sobre stock 10: solo una prevalece.

    Cada hilo sigue el contrato de servicios del ADR (lock pesimista +
    relectura del saldo dentro de la transacción). El perdedor observa el
    saldo ya reducido (2) y su movimiento dejaría saldo_posterior = -6:
    el CheckConstraint lo rechaza y su transacción completa se revierte.
    """
    oferta.stock = 10
    oferta.save(update_fields=["stock"])

    def salida():
        with transaction.atomic():
            actualizada = OfertaVideojuego.objects.select_for_update().get(
                pk=oferta.pk
            )
            saldo = actualizada.stock
            _movimiento(
                actualizada, tipo_salida,
                cantidad=8,
                saldo_anterior=saldo,
                saldo_posterior=saldo - 8,
            )
            actualizada.stock = saldo - 8
            actualizada.save(update_fields=["stock"])

    with ThreadPoolExecutor(max_workers=2) as pool:
        futuros = [pool.submit(_con_reintentos_de_lock, salida) for _ in range(2)]
        excepciones = [f.exception() for f in futuros]

    rechazados = [e for e in excepciones if e is not None]
    assert len(rechazados) == 1
    assert isinstance(rechazados[0], IntegrityError)

    oferta.refresh_from_db()
    assert oferta.stock == 2

    movimientos = Movimiento.objects.filter(oferta=oferta)
    assert movimientos.count() == 1
    assert movimientos.get().saldo_anterior == 10
    assert movimientos.get().saldo_posterior == 2
