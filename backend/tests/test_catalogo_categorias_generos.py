"""
Pruebas de las relaciones muchos-a-muchos de categorías y géneros (AZ-S1-16).

Se comprueba la protección real de la base de datos (sin ``full_clean``):
unicidad de cada pareja, integridad referencial, políticas ``on_delete`` y
cardinalidad 0/1/varias. Los filtros de las vistas se prueban contra la base
de datos para verificar que el JOIN del M2M no duplica ofertas.
"""
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.urls import reverse

from catalogo.models import (
    Categoria,
    Genero,
    OfertaVideojuego,
    Videojuego,
    VideojuegoCategoria,
    VideojuegoGenero,
)


# ── Unicidad de la pareja ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_pareja_videojuego_categoria_repetida_es_rechazada(videojuego, categoria):
    """``catalogo_videojuegocategoria_..._unicos``: pareja repetida → error."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            VideojuegoCategoria.objects.create(
                videojuego=videojuego, categoria=categoria
            )


@pytest.mark.django_db
def test_pareja_videojuego_genero_repetida_es_rechazada(videojuego, genero):
    """``catalogo_videojuegogenero_..._unicos``: pareja repetida → error."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            VideojuegoGenero.objects.create(videojuego=videojuego, genero=genero)


# ── Integridad referencial ────────────────────────────────────────────────────

@pytest.mark.django_db
def test_categoria_inexistente_es_rechazada(videojuego):
    """La FK a ``catalogo_categoria`` no admite ids que no existan."""
    # SQLite define las FKs como DEFERRABLE INITIALLY DEFERRED, por lo que la
    # violación no se detecta hasta comprobar las restricciones. PostgreSQL la
    # rechaza en el propio INSERT. Ambos caminos deben terminar en IntegrityError.
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            VideojuegoCategoria.objects.create(
                videojuego=videojuego, categoria_id=999999
            )
            connection.check_constraints()


@pytest.mark.django_db
def test_genero_inexistente_es_rechazado(videojuego):
    """La FK a ``catalogo_genero`` no admite ids que no existan."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            VideojuegoGenero.objects.create(videojuego=videojuego, genero_id=999999)
            connection.check_constraints()


# ── Políticas on_delete ───────────────────────────────────────────────────────

@pytest.mark.django_db
def test_borrar_videojuego_elimina_sus_vinculos(videojuego, categoria, genero):
    """``on_delete=CASCADE``: el vínculo no sobrevive al videojuego."""
    vinculo_categoria = VideojuegoCategoria.objects.get(videojuego=videojuego)
    vinculo_genero = VideojuegoGenero.objects.get(videojuego=videojuego)

    videojuego.delete()

    assert not VideojuegoCategoria.objects.filter(pk=vinculo_categoria.pk).exists()
    assert not VideojuegoGenero.objects.filter(pk=vinculo_genero.pk).exists()
    # Los catálogos no se tocan.
    assert Categoria.objects.filter(pk=categoria.pk).exists()
    assert Genero.objects.filter(pk=genero.pk).exists()


@pytest.mark.django_db
def test_borrar_categoria_en_uso_es_bloqueado(videojuego, categoria):
    """``on_delete=PROTECT``: una categoría asociada no puede borrarse."""
    with pytest.raises(ProtectedError):
        categoria.delete()


@pytest.mark.django_db
def test_borrar_genero_en_uso_es_bloqueado(videojuego, genero):
    """``on_delete=PROTECT``: un género asociado no puede borrarse."""
    with pytest.raises(ProtectedError):
        genero.delete()


# ── Cardinalidad 0, 1 y varias ────────────────────────────────────────────────

@pytest.mark.django_db
def test_videojuego_sin_categorias_ni_generos():
    """Un título puede existir sin clasificar (M2M ``blank=True``)."""
    juego = Videojuego.objects.create(titulo="Sin clasificar")

    assert juego.categorias.count() == 0
    assert juego.generos.count() == 0


@pytest.mark.django_db
def test_videojuego_con_una_categoria_y_un_genero(videojuego):
    """El fixture enlaza exactamente una categoría y un género."""
    assert videojuego.categorias.count() == 1
    assert videojuego.generos.count() == 1


@pytest.mark.django_db
def test_videojuego_con_varias_categorias_y_generos(videojuego):
    """Un título admite varias categorías y varios géneros a la vez."""
    otra_categoria = Categoria.objects.create(nombre="Aventura")
    otro_genero = Genero.objects.create(nombre="Mundo abierto")

    VideojuegoCategoria.objects.create(
        videojuego=videojuego, categoria=otra_categoria
    )
    VideojuegoGenero.objects.create(videojuego=videojuego, genero=otro_genero)

    assert videojuego.categorias.count() == 2
    assert videojuego.generos.count() == 2
    assert set(videojuego.categorias.values_list("nombre", flat=True)) == {
        "Acción",
        "Aventura",
    }
    assert set(videojuego.generos.values_list("nombre", flat=True)) == {
        "RPG",
        "Mundo abierto",
    }


# ── Filtros de vista con M2M (sin duplicados) ────────────────────────────────

@pytest.mark.django_db
def test_filtro_por_categoria_no_duplica_ofertas(
    client, oferta, videojuego, categoria
):
    """Filtrar por una categoría devuelve una sola oferta aunque el juego
    tenga varias categorías."""
    VideojuegoCategoria.objects.create(
        videojuego=videojuego, categoria=Categoria.objects.create(nombre="Aventura")
    )

    respuesta = client.get(reverse("catalogo:lista"), {"categoria": categoria.pk})

    assert respuesta.status_code == 200
    ofertas = list(respuesta.context["ofertas"])
    assert ofertas == [oferta]


@pytest.mark.django_db
def test_filtro_por_genero_no_duplica_ofertas(client, oferta, videojuego, genero):
    """Filtrar por un género devuelve una sola oferta aunque el juego tenga
    varios géneros."""
    VideojuegoGenero.objects.create(
        videojuego=videojuego, genero=Genero.objects.create(nombre="Mundo abierto")
    )

    respuesta = client.get(reverse("catalogo:lista"), {"genero": genero.pk})

    assert respuesta.status_code == 200
    assert list(respuesta.context["ofertas"]) == [oferta]


@pytest.mark.django_db
def test_filtro_por_categoria_excluye_otros_titulos(client, oferta, categoria, plataforma):
    """El filtro por categoría no arrastra ofertas de otras categorías."""
    otro_juego = Videojuego.objects.create(titulo="Otro Juego")
    VideojuegoCategoria.objects.create(
        videojuego=otro_juego,
        categoria=Categoria.objects.create(nombre="Deportes"),
    )
    OfertaVideojuego.objects.create(
        videojuego=otro_juego,
        plataforma=plataforma,
        precio_vigente=Decimal("1000.00"),
        sku="AZ-OTRO-001",
        stock=1,
    )

    respuesta = client.get(reverse("catalogo:lista"), {"categoria": categoria.pk})

    assert list(respuesta.context["ofertas"]) == [oferta]


@pytest.mark.django_db
def test_reporte_videojuegos_filtra_por_categoria(
    client, usuario_admin, oferta, categoria
):
    """El reporte administrativo usa el M2M y no duplica filas."""
    client.force_login(usuario_admin)

    respuesta = client.get(reverse("reportes:videojuegos"), {"categoria": categoria.pk})

    assert respuesta.status_code == 200
    assert list(respuesta.context["ofertas"]) == [oferta]


@pytest.mark.django_db
def test_reporte_inventario_muestra_las_categorias(client, usuario_admin, oferta):
    """La plantilla itera la relación M2M y muestra el nombre del catálogo."""
    client.force_login(usuario_admin)

    respuesta = client.get(reverse("reportes:inventario"))

    assert respuesta.status_code == 200
    assert "Acción" in respuesta.content.decode()
