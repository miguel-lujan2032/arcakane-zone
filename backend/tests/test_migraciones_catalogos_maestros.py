"""
Pruebas de las migraciones de catálogos maestros (AZ-S1-20).

Cubren:
  - La cadena desde el esquema anterior (0012) con datos conserva los títulos.
  - La semilla de clasificaciones e idiomas es idempotente.
  - La reversión con datos nuevos aborta con mensaje claro (tabla y cantidad).
  - La reversión sin datos nuevos restaura el esquema anterior.

No se prueba un backfill desde columnas de texto porque el esquema anterior
nunca las tuvo: ``Videojuego`` no almacenaba desarrolladora, distribuidora,
clasificación ni idioma. La normalización equivalente (mayúsculas y espacios)
se cubre en ``test_catalogos_maestros.py``.
"""
import importlib

import pytest
from django.apps import apps as global_apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


ANTERIOR = [("catalogo", "0012_oferta_estado_definitivo")]
TABLAS_NUEVAS = [
    "catalogo_desarrolladora",
    "catalogo_distribuidora",
    "catalogo_clasificacionedad",
    "catalogo_idioma",
    "catalogo_videojuegodesarrolladora",
    "catalogo_videojuegodistribuidora",
    "catalogo_videojuegoidioma",
]


def _migrate(targets=None):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    if targets is None:
        targets = executor.loader.graph.leaf_nodes()
    executor.migrate(targets)
    return executor


def _apps_at(nodes):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    return executor.loader.project_state(nodes).apps


@pytest.mark.django_db(transaction=True)
def test_migracion_crea_catalogos_y_conserva_datos_previos():
    """Desde 0012, la cadena crea las tablas nuevas y no toca los títulos."""
    _migrate(ANTERIOR)
    apps = _apps_at(ANTERIOR)

    Categoria = apps.get_model("catalogo", "Categoria")
    Genero = apps.get_model("catalogo", "Genero")
    Videojuego = apps.get_model("catalogo", "Videojuego")

    categoria = Categoria.objects.create(nombre="Acción")
    genero = Genero.objects.create(nombre="RPG")
    videojuego = Videojuego.objects.create(titulo="Juego previo", activo=True)
    apps.get_model("catalogo", "VideojuegoCategoria").objects.create(
        videojuego=videojuego, categoria=categoria
    )
    apps.get_model("catalogo", "VideojuegoGenero").objects.create(
        videojuego=videojuego, genero=genero
    )

    assert "catalogo_desarrolladora" not in connection.introspection.table_names()

    _migrate()

    from catalogo.models import (
        ClasificacionEdad,
        Idioma,
        Videojuego as VideojuegoActual,
    )

    assert VideojuegoActual.objects.filter(
        pk=videojuego.pk, titulo="Juego previo"
    ).exists()
    assert ClasificacionEdad.objects.filter(codigo="12").exists()
    assert Idioma.objects.filter(codigo="es").exists()

    tablas = connection.introspection.table_names()
    for tabla in TABLAS_NUEVAS:
        assert tabla in tablas


@pytest.mark.django_db(transaction=True)
def test_semilla_de_catalogos_es_idempotente():
    """Reejecutar la siembra no duplica clasificaciones ni idiomas."""
    _migrate()

    migracion = importlib.import_module(
        "catalogo.migrations.0014_semilla_catalogos_maestros"
    )
    from catalogo.models import ClasificacionEdad, Idioma

    ClasificacionEdad.objects.filter(codigo="18").delete()
    Idioma.objects.filter(codigo="ru").delete()

    migracion.sembrar(global_apps, None)
    migracion.sembrar(global_apps, None)

    assert ClasificacionEdad.objects.filter(codigo="18").exists()
    assert Idioma.objects.filter(codigo="ru").exists()
    assert ClasificacionEdad.objects.count() == len(migracion.CLASIFICACIONES)
    assert Idioma.objects.count() == len(migracion.IDIOMAS)


@pytest.mark.django_db(transaction=True)
def test_reversion_aborta_si_hay_desarrolladoras_vinculadas():
    """El esquema anterior no puede representar la relación: aborta claro."""
    _migrate()

    from catalogo.models import (
        Desarrolladora,
        Videojuego,
        VideojuegoDesarrolladora,
    )

    videojuego = Videojuego.objects.create(titulo="Con desarrolladora")
    desarrolladora = Desarrolladora.objects.create(
        codigo="estudio-reversible", nombre="Estudio Reversible"
    )
    VideojuegoDesarrolladora.objects.create(
        videojuego=videojuego, desarrolladora=desarrolladora
    )

    with pytest.raises(RuntimeError) as excinfo:
        _migrate(ANTERIOR)

    mensaje = str(excinfo.value)
    assert "catalogo_videojuegodesarrolladora" in mensaje
    assert "1 filas" in mensaje
    assert "Reversión de catalogo.0014 abortada" in mensaje

    # Limpieza: la migración sigue aplicada porque el reverso abortó.
    VideojuegoDesarrolladora.objects.all().delete()
    desarrolladora.delete()
    videojuego.delete()
    _migrate()


@pytest.mark.django_db(transaction=True)
def test_reversion_aborta_si_hay_clasificacion_asignada():
    """Una clasificación asignada también impide revertir sin pérdida."""
    _migrate()

    from catalogo.models import Videojuego

    videojuego = Videojuego.objects.create(
        titulo="Con clasificación", clasificacion_edad_id="12"
    )

    with pytest.raises(RuntimeError) as excinfo:
        _migrate(ANTERIOR)

    mensaje = str(excinfo.value)
    assert "catalogo_videojuego.clasificacion_edad" in mensaje
    assert "1 filas" in mensaje

    videojuego.delete()
    _migrate()


@pytest.mark.django_db(transaction=True)
def test_reversion_sin_datos_nuevos_restaura_esquema_anterior():
    """Sin relaciones nuevas, la reversión elimina las tablas y vuelve a aplicar."""
    _migrate()
    _migrate(ANTERIOR)

    tablas = connection.introspection.table_names()
    for tabla in TABLAS_NUEVAS:
        assert tabla not in tablas

    _migrate()

    tablas = connection.introspection.table_names()
    for tabla in TABLAS_NUEVAS:
        assert tabla in tablas
