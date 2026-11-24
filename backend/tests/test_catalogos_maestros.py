"""
Pruebas de los catálogos maestros del videojuego (AZ-S1-20).

Cubren unicidad de códigos, unicidad de nombre sin distinguir mayúsculas,
normalización de espacios, tablas puente M:N, tipos de idioma, clasificación
PEGI nullable y políticas de borrado (``PROTECT`` en catálogo, ``CASCADE`` en
el lado videojuego).

No hay columnas de texto legadas que migrar: el esquema anterior de
``Videojuego`` nunca almacenó desarrolladora, distribuidora, clasificación ni
idioma. La normalización se prueba sobre el helper usado por la semilla.
"""
import pytest
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError

from catalogo.models import (
    ClasificacionEdad,
    Desarrolladora,
    Distribuidora,
    Idioma,
    VideojuegoDesarrolladora,
    VideojuegoDistribuidora,
    VideojuegoIdioma,
    normalizar_nombre_catalogo,
)


# ── Normalización documentada ───────────────────────────────────────────────


def test_normalizar_nombre_catalogo_recorta_y_colapsa_espacios():
    assert normalizar_nombre_catalogo("  Rockstar   Games  ") == "Rockstar Games"
    assert normalizar_nombre_catalogo("PEGI\t12") == "PEGI 12"
    assert normalizar_nombre_catalogo("Español") == "Español"


# ── Unicidad de código ───────────────────────────────────────────────────────


@pytest.mark.django_db
def test_desarrolladora_codigo_unico():
    Desarrolladora.objects.create(codigo="estudio-x", nombre="Estudio X")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Desarrolladora.objects.create(codigo="estudio-x", nombre="Estudio Y")


@pytest.mark.django_db
def test_distribuidora_codigo_unico():
    Distribuidora.objects.create(codigo="dist-x", nombre="Distribuidora X")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Distribuidora.objects.create(codigo="dist-x", nombre="Distribuidora Y")


@pytest.mark.django_db
def test_clasificacion_edad_codigo_unico():
    ClasificacionEdad.objects.create(codigo="99", nombre="PEGI 99", orden=99)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ClasificacionEdad.objects.create(
                codigo="99", nombre="PEGI 100", orden=100
            )


@pytest.mark.django_db
def test_idioma_codigo_unico():
    Idioma.objects.create(codigo="xx", nombre="Idioma X")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Idioma.objects.create(codigo="xx", nombre="Idioma Y")


# ── Unicidad de nombre sin distinguir mayúsculas ────────────────────────────


@pytest.mark.django_db
def test_desarrolladora_nombre_unico_sin_mayusculas():
    Desarrolladora.objects.create(codigo="estudio-a", nombre="Estudio Alfa")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Desarrolladora.objects.create(codigo="estudio-b", nombre="ESTUDIO ALFA")


@pytest.mark.django_db
def test_distribuidora_nombre_unico_sin_mayusculas():
    Distribuidora.objects.create(codigo="dist-a", nombre="Distribuidora Alfa")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Distribuidora.objects.create(
                codigo="dist-b", nombre="DISTRIBUIDORA ALFA"
            )


@pytest.mark.django_db
def test_idioma_nombre_unico_sin_mayusculas():
    Idioma.objects.create(codigo="xx", nombre="Idioma Alfa")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Idioma.objects.create(codigo="xy", nombre="IDIOMA ALFA")


@pytest.mark.django_db
def test_clasificacion_edad_nombre_unico():
    ClasificacionEdad.objects.create(codigo="99", nombre="PEGI 99", orden=99)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ClasificacionEdad.objects.create(
                codigo="100", nombre="PEGI 99", orden=100
            )


@pytest.mark.django_db
def test_clasificacion_edad_se_ordena_por_orden():
    codigos = list(ClasificacionEdad.objects.values_list("codigo", flat=True))
    assert codigos == ["3", "7", "12", "16", "18"]


# ── Tablas puente: desarrolladora y distribuidora ───────────────────────────


@pytest.mark.django_db
def test_videojuego_con_varias_desarrolladoras_y_distribuidoras(
    videojuego,
    desarrolladora,
    desarrolladora_alternativa,
    distribuidora,
    distribuidora_alternativa,
):
    VideojuegoDesarrolladora.objects.create(
        videojuego=videojuego, desarrolladora=desarrolladora
    )
    VideojuegoDesarrolladora.objects.create(
        videojuego=videojuego, desarrolladora=desarrolladora_alternativa
    )
    VideojuegoDistribuidora.objects.create(
        videojuego=videojuego, distribuidora=distribuidora
    )
    VideojuegoDistribuidora.objects.create(
        videojuego=videojuego, distribuidora=distribuidora_alternativa
    )

    assert set(videojuego.desarrolladoras.values_list("codigo", flat=True)) == {
        "rockstar-games",
        "cd-projekt-red",
    }
    assert set(videojuego.distribuidoras.values_list("codigo", flat=True)) == {
        "sony-interactive",
        "bandai-namco",
    }


@pytest.mark.django_db
def test_par_desarrolladora_duplicado_rechazado(videojuego, desarrolladora):
    VideojuegoDesarrolladora.objects.create(
        videojuego=videojuego, desarrolladora=desarrolladora
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            VideojuegoDesarrolladora.objects.create(
                videojuego=videojuego, desarrolladora=desarrolladora
            )


@pytest.mark.django_db
def test_par_distribuidora_duplicado_rechazado(videojuego, distribuidora):
    VideojuegoDistribuidora.objects.create(
        videojuego=videojuego, distribuidora=distribuidora
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            VideojuegoDistribuidora.objects.create(
                videojuego=videojuego, distribuidora=distribuidora
            )


@pytest.mark.django_db
def test_protect_desarrolladora_y_distribuidora_en_uso(
    videojuego, desarrolladora, distribuidora
):
    VideojuegoDesarrolladora.objects.create(
        videojuego=videojuego, desarrolladora=desarrolladora
    )
    VideojuegoDistribuidora.objects.create(
        videojuego=videojuego, distribuidora=distribuidora
    )

    with pytest.raises(ProtectedError):
        desarrolladora.delete()
    with pytest.raises(ProtectedError):
        distribuidora.delete()


@pytest.mark.django_db
def test_cascade_videojuego_elimina_puentes_de_desarrolladora_y_distribuidora(
    videojuego, desarrolladora, distribuidora
):
    vinculo_dev = VideojuegoDesarrolladora.objects.create(
        videojuego=videojuego, desarrolladora=desarrolladora
    )
    vinculo_dist = VideojuegoDistribuidora.objects.create(
        videojuego=videojuego, distribuidora=distribuidora
    )
    ids = (vinculo_dev.pk, vinculo_dist.pk)

    videojuego.delete()

    assert not VideojuegoDesarrolladora.objects.filter(pk=ids[0]).exists()
    assert not VideojuegoDistribuidora.objects.filter(pk=ids[1]).exists()
    assert Desarrolladora.objects.filter(pk=desarrolladora.pk).exists()
    assert Distribuidora.objects.filter(pk=distribuidora.pk).exists()


# ── Clasificación por edad ──────────────────────────────────────────────────


@pytest.mark.django_db
def test_videojuego_sin_clasificacion_edad_es_valido(videojuego):
    assert videojuego.clasificacion_edad_id is None


@pytest.mark.django_db
def test_videojuego_acepta_clasificacion_existente(videojuego, clasificacion_edad):
    videojuego.clasificacion_edad = clasificacion_edad
    videojuego.save()

    videojuego.refresh_from_db()
    assert videojuego.clasificacion_edad_id == "12"
    assert videojuego.clasificacion_edad.nombre == "PEGI 12"


@pytest.mark.django_db
def test_videojuego_rechaza_clasificacion_inexistente(videojuego):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            videojuego.clasificacion_edad_id = "99"
            videojuego.save()
            connection.check_constraints()


@pytest.mark.django_db
def test_protect_clasificacion_edad_en_uso(videojuego, clasificacion_edad):
    videojuego.clasificacion_edad = clasificacion_edad
    videojuego.save()

    with pytest.raises(ProtectedError):
        clasificacion_edad.delete()


# ── Idiomas por tipo ────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_mismo_idioma_con_tipos_distintos_permitido(videojuego, idioma):
    for tipo in ("audio", "interfaz", "subtitulos"):
        VideojuegoIdioma.objects.create(
            videojuego=videojuego, idioma=idioma, tipo=tipo
        )

    assert VideojuegoIdioma.objects.filter(
        videojuego=videojuego, idioma=idioma
    ).count() == 3


@pytest.mark.django_db
def test_idioma_duplicado_por_tipo_rechazado(videojuego, idioma):
    VideojuegoIdioma.objects.create(
        videojuego=videojuego, idioma=idioma, tipo="audio"
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            VideojuegoIdioma.objects.create(
                videojuego=videojuego, idioma=idioma, tipo="audio"
            )


@pytest.mark.django_db
def test_idioma_tipo_invalido_rechazado(videojuego, idioma):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            VideojuegoIdioma.objects.create(
                videojuego=videojuego, idioma=idioma, tipo="doblaje"
            )


@pytest.mark.django_db
def test_protect_idioma_en_uso(videojuego, idioma):
    VideojuegoIdioma.objects.create(
        videojuego=videojuego, idioma=idioma, tipo="subtitulos"
    )
    with pytest.raises(ProtectedError):
        idioma.delete()


@pytest.mark.django_db
def test_cascade_videojuego_elimina_puente_de_idioma(videojuego, idioma):
    vinculo = VideojuegoIdioma.objects.create(
        videojuego=videojuego, idioma=idioma, tipo="interfaz"
    )
    pk = vinculo.pk

    videojuego.delete()

    assert not VideojuegoIdioma.objects.filter(pk=pk).exists()
    assert Idioma.objects.filter(pk=idioma.pk).exists()
