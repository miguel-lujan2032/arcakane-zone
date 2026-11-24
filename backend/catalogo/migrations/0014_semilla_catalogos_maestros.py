"""
Siembra idempotente de los catálogos maestros (AZ-S1-20).

Paso 2 (datos). No existen columnas de texto antiguas que migrar: el esquema
anterior de ``Videojuego`` nunca almacenó desarrolladora, distribuidora,
clasificación por edad ni idioma. Por eso esta migración solo siembra los
valores de referencia de clasificación PEGI e idiomas comunes.

La reversión es segura: aborta con un ``RuntimeError`` descriptivo si algún
videojuego usa las relaciones nuevas o si existen filas de catálogo fuera de
los valores sembrados; de lo contrario elimina solo los valores sembrados.
"""
from django.db import migrations
from django.db.models.deletion import ProtectedError


CLASIFICACIONES = [
    ("3", "PEGI 3", 3),
    ("7", "PEGI 7", 7),
    ("12", "PEGI 12", 12),
    ("16", "PEGI 16", 16),
    ("18", "PEGI 18", 18),
]

IDIOMAS = [
    ("es", "Español"),
    ("en", "Inglés"),
    ("fr", "Francés"),
    ("de", "Alemán"),
    ("it", "Italiano"),
    ("pt", "Portugués"),
    ("ja", "Japonés"),
    ("ko", "Coreano"),
    ("zh", "Chino"),
    ("ru", "Ruso"),
]


def _normalizar(valor):
    """Recorta extremos y colapsa espacios internos (misma regla que el modelo)."""
    return " ".join(valor.split())


def sembrar(apps, schema_editor):
    ClasificacionEdad = apps.get_model("catalogo", "ClasificacionEdad")
    Idioma = apps.get_model("catalogo", "Idioma")

    for codigo, nombre, orden in CLASIFICACIONES:
        ClasificacionEdad.objects.get_or_create(
            codigo=codigo,
            defaults={"nombre": _normalizar(nombre), "orden": orden},
        )
    for codigo, nombre in IDIOMAS:
        Idioma.objects.get_or_create(
            codigo=codigo,
            defaults={"nombre": _normalizar(nombre)},
        )


def deshacer(apps, schema_editor):
    Videojuego = apps.get_model("catalogo", "Videojuego")
    VideojuegoDesarrolladora = apps.get_model("catalogo", "VideojuegoDesarrolladora")
    VideojuegoDistribuidora = apps.get_model("catalogo", "VideojuegoDistribuidora")
    VideojuegoIdioma = apps.get_model("catalogo", "VideojuegoIdioma")
    Desarrolladora = apps.get_model("catalogo", "Desarrolladora")
    Distribuidora = apps.get_model("catalogo", "Distribuidora")
    ClasificacionEdad = apps.get_model("catalogo", "ClasificacionEdad")
    Idioma = apps.get_model("catalogo", "Idioma")

    problemas = []
    for modelo, tabla in [
        (VideojuegoDesarrolladora, "catalogo_videojuegodesarrolladora"),
        (VideojuegoDistribuidora, "catalogo_videojuegodistribuidora"),
        (VideojuegoIdioma, "catalogo_videojuegoidioma"),
    ]:
        total = modelo.objects.count()
        if total:
            problemas.append(f"'{tabla}' ({total} filas)")

    con_clasificacion = Videojuego.objects.filter(
        clasificacion_edad__isnull=False
    ).count()
    if con_clasificacion:
        problemas.append(
            "'catalogo_videojuego.clasificacion_edad' "
            f"({con_clasificacion} filas)"
        )

    codigos_clasificacion = {codigo for codigo, _, _ in CLASIFICACIONES}
    codigos_idioma = {codigo for codigo, _ in IDIOMAS}
    extras = [
        (
            "catalogo_clasificacionedad",
            ClasificacionEdad.objects.exclude(
                codigo__in=codigos_clasificacion
            ).count(),
        ),
        (
            "catalogo_idioma",
            Idioma.objects.exclude(codigo__in=codigos_idioma).count(),
        ),
        ("catalogo_desarrolladora", Desarrolladora.objects.count()),
        ("catalogo_distribuidora", Distribuidora.objects.count()),
    ]
    for tabla, total in extras:
        if total:
            problemas.append(f"'{tabla}' ({total} filas)")

    if problemas:
        raise RuntimeError(
            "Reversión de catalogo.0014 abortada: el esquema anterior no puede "
            "representar los catálogos maestros y se perderían datos en: "
            + ", ".join(problemas)
            + ". Elimine o migre esas filas antes de revertir."
        )

    for codigo, _, _ in CLASIFICACIONES:
        try:
            ClasificacionEdad.objects.filter(codigo=codigo).delete()
        except ProtectedError as exc:
            tablas = sorted({obj._meta.db_table for obj in exc.protected_objects})
            raise RuntimeError(
                "No se pueden eliminar las clasificaciones por edad sembradas: "
                f"hay filas que las referencian ({', '.join(tablas)}). "
                f"Código: '{codigo}'. Vacíe o migre esas filas antes de revertir."
            ) from exc

    for codigo, _ in IDIOMAS:
        try:
            Idioma.objects.filter(codigo=codigo).delete()
        except ProtectedError as exc:
            tablas = sorted({obj._meta.db_table for obj in exc.protected_objects})
            raise RuntimeError(
                "No se pueden eliminar los idiomas sembrados: hay filas que los "
                f"referencian ({', '.join(tablas)}). Código: '{codigo}'. "
                "Vacíe o migre esas filas antes de revertir."
            ) from exc


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0013_catalogos_maestros"),
    ]

    operations = [
        migrations.RunPython(sembrar, reverse_code=deshacer),
    ]
