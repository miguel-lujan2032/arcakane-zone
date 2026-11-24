"""
Pruebas de los catálogos de estado y sus FKs (AZ-S1-17).

Verifica unicidad de códigos, integridad referencial, PROTECT y que editar la
etiqueta no altera los datos transaccionales.
"""
import pytest
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError

from catalogo.models import EstadoPublicacion
from pagos.models import EstadoIntentoPago, IntentoPago
from pedidos.models import EstadoPedido, Pedido


# ── Códigos únicos ───────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_codigo_estado_pedido_unico():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            EstadoPedido.objects.create(codigo="pendiente", nombre="Duplicado")


@pytest.mark.django_db
def test_codigo_estado_intento_pago_unico():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            EstadoIntentoPago.objects.create(codigo="aprobado", nombre="Duplicado")


@pytest.mark.django_db
def test_codigo_estado_publicacion_unico():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            EstadoPublicacion.objects.create(codigo="publicado", nombre="Duplicado")


# ── FK a estado inexistente ──────────────────────────────────────────────────


@pytest.mark.django_db
def test_pedido_rechaza_estado_inexistente(usuario_cliente):
    # SQLite difiere la comprobación de FKs; en PostgreSQL falla en el INSERT.
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Pedido.objects.create(cliente=usuario_cliente, estado_id="inexistente")
            connection.check_constraints()


@pytest.mark.django_db
def test_pago_rechaza_estado_inexistente(pedido_con_item):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IntentoPago.objects.create(
                pedido=pedido_con_item,
                importe=pedido_con_item.total,
                estado_id="inexistente",
                referencia="REF-EST-INEX",
            )
            connection.check_constraints()


@pytest.mark.django_db
def test_oferta_rechaza_estado_publicacion_inexistente(videojuego, plataforma):
    from catalogo.models import OfertaVideojuego

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            OfertaVideojuego.objects.create(
                videojuego=videojuego,
                plataforma=plataforma,
                precio_vigente=1000,
                sku="AZ-INV-EST-1",
                estado_publicacion_id="inexistente",
            )
            connection.check_constraints()


# ── PROTECT al borrar estado en uso ──────────────────────────────────────────


@pytest.mark.django_db
def test_no_se_puede_borrar_estado_pedido_en_uso(pedido_con_item):
    estado = EstadoPedido.objects.get(codigo="pendiente")
    with pytest.raises(ProtectedError):
        estado.delete()


@pytest.mark.django_db
def test_no_se_puede_borrar_estado_pago_en_uso(pedido_con_item):
    intento = IntentoPago.objects.create(
        pedido=pedido_con_item,
        importe=pedido_con_item.total,
        estado_id="aprobado",
        referencia="REF-EST-USO",
    )
    estado = EstadoIntentoPago.objects.get(codigo="aprobado")
    with pytest.raises(ProtectedError):
        estado.delete()
    assert IntentoPago.objects.filter(pk=intento.pk).exists()


@pytest.mark.django_db
def test_no_se_puede_borrar_estado_publicacion_en_uso(oferta):
    estado = EstadoPublicacion.objects.get(codigo="publicado")
    with pytest.raises(ProtectedError):
        estado.delete()


# ── Etiquetas modificables sin alterar datos transaccionales ─────────────────


@pytest.mark.django_db
def test_etiqueta_pedido_editable_sin_alterar_transaccionales(pedido_con_item):
    estado = EstadoPedido.objects.get(codigo="pendiente")
    estado.nombre = "En espera"
    estado.descripcion = "Etiqueta modificada para prueba."
    estado.save()

    pedido_con_item.refresh_from_db()
    assert pedido_con_item.estado_id == "pendiente"
    assert pedido_con_item.estado.codigo == "pendiente"
    assert pedido_con_item.estado.nombre == "En espera"


@pytest.mark.django_db
def test_etiqueta_pago_editable_sin_alterar_transaccionales(pedido_con_item):
    intento = IntentoPago.objects.create(
        pedido=pedido_con_item,
        importe=pedido_con_item.total,
        estado_id="aprobado",
        referencia="REF-EST-LBL",
    )
    estado = EstadoIntentoPago.objects.get(codigo="aprobado")
    estado.nombre = "Confirmado"
    estado.save()

    intento.refresh_from_db()
    assert intento.estado_id == "aprobado"
    assert intento.estado.nombre == "Confirmado"


@pytest.mark.django_db
def test_etiqueta_publicacion_editable_sin_alterar_transaccionales(oferta):
    estado = EstadoPublicacion.objects.get(codigo="publicado")
    estado.nombre = "Visible"
    estado.save()

    oferta.refresh_from_db()
    assert oferta.estado_publicacion_id == "publicado"
    assert oferta.estado_publicacion.nombre == "Visible"
