"""
Pruebas de integridad referencial y unicidad del catálogo comercial (AZ-S1-13):
  - Un videojuego puede venderse en varias plataformas.
  - Cada oferta tiene precio, SKU y disponibilidad propios.
  - No hay duplicados de la combinación comercial (videojuego, plataforma).
  - Los detalles históricos no cambian si cambia el catálogo.
"""
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError

from catalogo.models import OfertaVideojuego, Videojuego
from pedidos.models import DetallePedido, Pedido


# ── Unicidad de la combinación comercial ─────────────────────────────────────

@pytest.mark.django_db
def test_un_videojuego_puede_venderse_en_varias_plataformas(
    videojuego, plataforma, plataforma_alternativa
):
    """El mismo título admite ofertas simultáneas en distintas plataformas."""
    OfertaVideojuego.objects.create(
        videojuego=videojuego, plataforma=plataforma,
        precio_vigente=Decimal("100.00"), sku="AZ-MULTI-01", stock=5,
    )
    OfertaVideojuego.objects.create(
        videojuego=videojuego, plataforma=plataforma_alternativa,
        precio_vigente=Decimal("120.00"), sku="AZ-MULTI-02", stock=3,
    )

    ofertas = videojuego.ofertas.all()
    assert ofertas.count() == 2
    assert {o.plataforma.nombre for o in ofertas} == {"PC", "PlayStation 5"}


@pytest.mark.django_db
def test_no_duplicados_de_combinacion_videojuego_plataforma(
    videojuego, plataforma, oferta
):
    """La combinación videojuego-plataforma es única en el catálogo."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            OfertaVideojuego.objects.create(
                videojuego=videojuego, plataforma=plataforma,
                precio_vigente=Decimal("90.00"), sku="AZ-DUP-001", stock=1,
            )


@pytest.mark.django_db
def test_sku_unico(videojuego, plataforma_alternativa, oferta):
    """Dos ofertas no pueden compartir el mismo SKU interno."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            OfertaVideojuego.objects.create(
                videojuego=videojuego, plataforma=plataforma_alternativa,
                precio_vigente=Decimal("90.00"), sku=oferta.sku, stock=1,
            )


# ── Restricciones de dominio ─────────────────────────────────────────────────

@pytest.mark.django_db
def test_precio_vigente_no_puede_ser_negativo(videojuego, plataforma):
    """El precio vigente de la oferta está restringido a valores no negativos."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            OfertaVideojuego.objects.create(
                videojuego=videojuego, plataforma=plataforma,
                precio_vigente=Decimal("-1.00"), sku="AZ-NEG-001", stock=1,
            )


# ── Integridad referencial (políticas on_delete) ─────────────────────────────

@pytest.mark.django_db
def test_no_se_puede_borrar_videojuego_con_ofertas(oferta):
    """Un título con ofertas está protegido contra borrado (PROTECT)."""
    with pytest.raises(ProtectedError):
        oferta.videojuego.delete()


@pytest.mark.django_db
def test_no_se_puede_borrar_plataforma_con_ofertas(oferta):
    """Una plataforma referenciada por ofertas está protegida (PROTECT)."""
    with pytest.raises(ProtectedError):
        oferta.plataforma.delete()


@pytest.mark.django_db
def test_no_se_puede_borrar_oferta_con_detalles(pedido_con_item):
    """Una oferta adquirida en pedidos históricos está protegida (PROTECT)."""
    detalle = pedido_con_item.detalles.first()
    with pytest.raises(ProtectedError):
        detalle.oferta.delete()


@pytest.mark.django_db
def test_borrar_pedido_borra_sus_detalles_pero_no_las_ofertas(
    pedido_con_item, oferta
):
    """El pedido es dueño de sus detalles (CASCADE); la oferta sobrevive."""
    detalle_pk = pedido_con_item.detalles.first().pk
    pedido_con_item.delete()

    assert not DetallePedido.objects.filter(pk=detalle_pk).exists()
    assert OfertaVideojuego.objects.filter(pk=oferta.pk).exists()


# ── Unicidad de líneas del pedido ─────────────────────────────────────────────

@pytest.mark.django_db
def test_detalle_unico_por_pedido_y_oferta(pedido_con_item, oferta):
    """No puede existir dos líneas del mismo pedido para la misma oferta."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            DetallePedido.objects.create(
                pedido=pedido_con_item, oferta=oferta,
                cantidad=1, precio_unitario=Decimal("10.00"),
            )


# ── Inmutabilidad histórica ──────────────────────────────────────────────────

@pytest.mark.django_db
def test_detalle_congela_precio_titulo_y_plataforma(usuario_cliente, oferta):
    """Los detalles históricos no cambian aunque el catálogo se modifique."""
    pedido = Pedido.objects.create(
        cliente=usuario_cliente, estado=Pedido.Estado.PAGADO
    )
    detalle = DetallePedido.objects.create(
        pedido=pedido, oferta=oferta, cantidad=1,
        precio_unitario=oferta.precio_vigente,
    )
    assert detalle.titulo_snapshot == "Juego Alpha"
    assert detalle.plataforma_snapshot == "PC"

    # El catálogo cambia después de la compra
    oferta.videojuego.titulo = "Juego Renombrado"
    oferta.videojuego.save()
    oferta.plataforma.nombre = "PC Pro"
    oferta.plataforma.save()
    oferta.precio_vigente = Decimal("99000")
    oferta.save()

    detalle.refresh_from_db()
    assert detalle.precio_unitario == Decimal("80000")
    assert detalle.titulo_snapshot == "Juego Alpha"
    assert detalle.plataforma_snapshot == "PC"


# ── Estado de publicación y disponibilidad ─────────────────────────────────────

@pytest.mark.django_db
def test_manager_publicadas_filtra_por_estado(videojuego, plataforma, plataforma_alternativa):
    """El queryset de dominio expone solo las ofertas publicadas."""
    from catalogo.models import Plataforma

    switch = Plataforma.objects.create(nombre="Nintendo Switch")
    publicada = OfertaVideojuego.objects.create(
        videojuego=videojuego, plataforma=plataforma,
        precio_vigente=Decimal("10.00"), sku="AZ-PUB-01", stock=9,
        estado_publicacion=OfertaVideojuego.EstadoPublicacion.PUBLICADO,
    )
    OfertaVideojuego.objects.create(
        videojuego=videojuego, plataforma=plataforma_alternativa,
        precio_vigente=Decimal("1.00"), sku="AZ-BORR-01", stock=9,
        estado_publicacion=OfertaVideojuego.EstadoPublicacion.BORRADOR,
    )
    OfertaVideojuego.objects.create(
        videojuego=videojuego, plataforma=switch,
        precio_vigente=Decimal("1.00"), sku="AZ-RETI-01", stock=9,
        estado_publicacion=OfertaVideojuego.EstadoPublicacion.RETIRADO,
    )

    publicadas = videojuego.ofertas.publicadas()
    assert publicadas.count() == 1
    assert publicadas.first().pk == publicada.pk


@pytest.mark.django_db
def test_disponible_requiere_publicacion_y_stock(videojuego, plataforma):
    oferta = OfertaVideojuego.objects.create(
        videojuego=videojuego, plataforma=plataforma,
        precio_vigente=Decimal("10.00"), sku="AZ-DISP-01", stock=5,
    )
    assert oferta.disponible is True

    oferta.stock = 0
    assert oferta.disponible is False

    oferta.stock = 3
    oferta.estado_publicacion = OfertaVideojuego.EstadoPublicacion.RETIRADO
    assert oferta.disponible is False


@pytest.mark.django_db
def test_videojuego_disponible_agrega_sus_ofertas(
    videojuego, plataforma, plataforma_alternativa
):
    """El título es vendible si al menos una de sus ofertas lo es."""
    assert videojuego.disponible is False  # sin ofertas

    agotada = OfertaVideojuego.objects.create(
        videojuego=videojuego, plataforma=plataforma,
        precio_vigente=Decimal("10.00"), sku="AZ-VJ-D01", stock=0,
    )
    vendible = OfertaVideojuego.objects.create(
        videojuego=videojuego, plataforma=plataforma_alternativa,
        precio_vigente=Decimal("10.00"), sku="AZ-VJ-D02", stock=2,
    )
    assert videojuego.disponible is True

    vendible.stock = 0
    vendible.save()
    agotada.refresh_from_db()
    assert videojuego.disponible is False
