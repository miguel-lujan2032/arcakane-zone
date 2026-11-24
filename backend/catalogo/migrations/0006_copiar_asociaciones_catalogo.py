"""
Migración de datos: copia las categorías y géneros existentes a las tablas
puente (AZ-S1-16).

Cada videojuego que hoy tiene ``categoria_id`` y/o ``genero_id`` recibe una
asociación inicial en ``VideojuegoCategoria`` / ``VideojuegoGenero``. La
operación es idempotente: si se re-ejecuta, ``ignore_conflicts`` descarta las
parejas ya existentes en lugar de fallar por unicidad.

Reversibilidad
--------------
Al revertir, el esquema antiguo solo admite **una** categoría y **un** género
por videojuego. La reversión restaura la asociación de menor PK de cada tabla
puente (la más antigua) y **descarta las asociaciones adicionales** creadas
después de la normalización. Si algún videojuego no tiene categoría o género,
aborta con un ``RuntimeError`` descriptivo en lugar de escribir NULL, porque la
columna antigua era ``NOT NULL`` y un silencio produciría datos inválidos.
"""
from django.db import migrations


def copiar_asociaciones(apps, schema_editor):
    """Copia la categoría y el género actuales como asociación inicial."""
    Videojuego = apps.get_model("catalogo", "Videojuego")
    VideojuegoCategoria = apps.get_model("catalogo", "VideojuegoCategoria")
    VideojuegoGenero = apps.get_model("catalogo", "VideojuegoGenero")

    categorias = [
        VideojuegoCategoria(videojuego_id=pk, categoria_id=categoria_id)
        for pk, categoria_id in Videojuego.objects.exclude(
            categoria_id=None
        ).values_list("pk", "categoria_id")
    ]
    generos = [
        VideojuegoGenero(videojuego_id=pk, genero_id=genero_id)
        for pk, genero_id in Videojuego.objects.exclude(genero_id=None).values_list(
            "pk", "genero_id"
        )
    ]

    VideojuegoCategoria.objects.bulk_create(categorias, ignore_conflicts=True)
    VideojuegoGenero.objects.bulk_create(generos, ignore_conflicts=True)


def _primer_valor(through, campo):
    """Devuelve {videojuego_id: valor_id} conservando la fila de menor PK."""
    mapa = {}
    for videojuego_id, valor_id in through.objects.order_by("pk").values_list(
        "videojuego_id", campo
    ):
        mapa.setdefault(videojuego_id, valor_id)
    return mapa


def restaurar_asociaciones(apps, schema_editor):
    """Revierte a una única categoría/género por videojuego (la más antigua)."""
    Videojuego = apps.get_model("catalogo", "Videojuego")
    VideojuegoCategoria = apps.get_model("catalogo", "VideojuegoCategoria")
    VideojuegoGenero = apps.get_model("catalogo", "VideojuegoGenero")

    categorias = _primer_valor(VideojuegoCategoria, "categoria_id")
    generos = _primer_valor(VideojuegoGenero, "genero_id")
    ids = list(Videojuego.objects.values_list("pk", flat=True))

    sin_categoria = [pk for pk in ids if pk not in categorias]
    sin_genero = [pk for pk in ids if pk not in generos]
    if sin_categoria or sin_genero:
        raise RuntimeError(
            "No se puede revertir la normalización de categorías/géneros: "
            f"{len(sin_categoria)} videojuego(s) sin categoría y "
            f"{len(sin_genero)} sin género. "
            f"IDs sin categoría: {sin_categoria[:10]}; "
            f"IDs sin género: {sin_genero[:10]}. "
            "Asigne una categoría y un género a cada videojuego antes de revertir."
        )

    for pk in ids:
        Videojuego.objects.filter(pk=pk).update(
            categoria_id=categorias[pk], genero_id=generos[pk]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0005_videojuego_categoria_genero_opcionales"),
    ]

    operations = [
        migrations.RunPython(copiar_asociaciones, restaurar_asociaciones),
    ]
