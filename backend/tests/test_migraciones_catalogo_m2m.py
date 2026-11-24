"""
Pruebas de las migraciones de normalización de categorías/géneros (AZ-S1-16).

Cubren:
  - La cadena desde el esquema anterior vacío crea las tablas puente.
  - Un videojuego con categoría y género termina con su asociación inicial.
  - La copia de datos es idempotente.
  - La reversión restaura la primera asociación (menor PK) y descarta el resto.
  - La reversión aborta con un mensaje claro si falta categoría o género.
"""
import importlib

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from catalogo.models import (
    Categoria,
    Genero,
    Videojuego,
    VideojuegoCategoria,
    VideojuegoGenero,
)

ANTERIOR = [("catalogo", "0003_indices_catalogo")]
PUENTES = [("catalogo", "0006_copiar_asociaciones_catalogo")]


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


def _crear_legado(apps, titulo="Juego Legado", categoria="Acción", genero="RPG"):
    """Crea un videojuego con el esquema anterior (FKs directas)."""
    CategoriaVieja = apps.get_model("catalogo", "Categoria")
    GeneroViejo = apps.get_model("catalogo", "Genero")
    VideojuegoViejo = apps.get_model("catalogo", "Videojuego")

    return VideojuegoViejo.objects.create(
        titulo=titulo,
        categoria=CategoriaVieja.objects.create(nombre=categoria),
        genero=GeneroViejo.objects.create(nombre=genero),
    )


@pytest.mark.django_db(transaction=True)
def test_cadena_m2m_desde_esquema_anterior_vacio():
    """Desde 0003 sin datos, la cadena crea las tablas puente vacías."""
    _migrate(ANTERIOR)

    tablas = connection.introspection.table_names()
    assert "catalogo_videojuegocategoria" not in tablas
    assert "catalogo_videojuegogenero" not in tablas

    _migrate()

    tablas = connection.introspection.table_names()
    assert "catalogo_videojuegocategoria" in tablas
    assert "catalogo_videojuegogenero" in tablas
    assert VideojuegoCategoria.objects.count() == 0
    assert VideojuegoGenero.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_migracion_copia_asociaciones_e_es_idempotente():
    """Cada categoría/género actual se copia una sola vez a su tabla puente."""
    _migrate(ANTERIOR)
    apps_anterior = _apps_at(ANTERIOR)
    vj = _crear_legado(apps_anterior, titulo="Juego Legado")

    # 0006 se aplica una vez durante la migración.
    _migrate(PUENTES)
    apps_puentes = _apps_at(PUENTES)
    CategoriaPuente = apps_puentes.get_model("catalogo", "VideojuegoCategoria")
    GeneroPuente = apps_puentes.get_model("catalogo", "VideojuegoGenero")

    assert CategoriaPuente.objects.count() == 1
    assert GeneroPuente.objects.count() == 1

    # Re-ejecutar la copia no duplica filas (ignore_conflicts).
    migracion = importlib.import_module(
        "catalogo.migrations.0006_copiar_asociaciones_catalogo"
    )
    migracion.copiar_asociaciones(apps_puentes, None)
    migracion.copiar_asociaciones(apps_puentes, None)

    assert CategoriaPuente.objects.count() == 1
    assert GeneroPuente.objects.count() == 1

    # Estado final: el videojuego conserva su asociación inicial.
    _migrate()
    juego = Videojuego.objects.get(pk=vj.pk)
    assert list(juego.categorias.values_list("nombre", flat=True)) == ["Acción"]
    assert list(juego.generos.values_list("nombre", flat=True)) == ["RPG"]


@pytest.mark.django_db(transaction=True)
def test_reversion_restaura_la_primera_asociacion():
    """Al revertir solo cabe una categoría/género: se conserva la de menor PK."""
    _migrate(ANTERIOR)
    apps_anterior = _apps_at(ANTERIOR)
    vj = _crear_legado(
        apps_anterior, titulo="Juego Reversible", categoria="Acción", genero="RPG"
    )
    _migrate()

    # El esquema nuevo permite ampliar las asociaciones.
    juego = Videojuego.objects.get(pk=vj.pk)
    VideojuegoCategoria.objects.create(
        videojuego=juego, categoria=Categoria.objects.create(nombre="Aventura")
    )
    VideojuegoGenero.objects.create(
        videojuego=juego, genero=Genero.objects.create(nombre="Mundo abierto")
    )
    assert juego.categorias.count() == 2
    assert juego.generos.count() == 2

    _migrate(ANTERIOR)

    apps_legacy = _apps_at(ANTERIOR)
    VideojuegoLegacy = apps_legacy.get_model("catalogo", "Videojuego")
    juego_legacy = VideojuegoLegacy.objects.get(pk=vj.pk)
    # La asociación más antigua (menor PK) es la que existía antes de normalizar.
    assert juego_legacy.categoria.nombre == "Acción"
    assert juego_legacy.genero.nombre == "RPG"

    # La cadena vuelve a aplicar limpiamente.
    _migrate()
    juego = Videojuego.objects.get(pk=vj.pk)
    assert list(juego.categorias.values_list("nombre", flat=True)) == ["Acción"]
    assert list(juego.generos.values_list("nombre", flat=True)) == ["RPG"]


@pytest.mark.django_db(transaction=True)
def test_reversion_aborta_si_falta_categoria_o_genero():
    """Sin categoría/género no se puede rellenar la columna NOT NULL del esquema viejo."""
    _migrate(ANTERIOR)
    apps_anterior = _apps_at(ANTERIOR)
    _crear_legado(apps_anterior, titulo="Juego Completo")
    _migrate()

    # Un título creado bajo el esquema nuevo puede no tener clasificación.
    Videojuego.objects.create(titulo="Sin clasificar")

    with pytest.raises(RuntimeError, match="sin categoría"):
        _migrate(ANTERIOR)

    # La cadena se restaura para no contaminar el resto de la sesión.
    _migrate()
    assert "catalogo_videojuegocategoria" in connection.introspection.table_names()
