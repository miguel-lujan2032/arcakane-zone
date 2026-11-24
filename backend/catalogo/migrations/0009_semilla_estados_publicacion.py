"""
Siembra idempotente del catálogo de estados de publicación (AZ-S1-17).

Paso 2 (datos). El reverso falla con mensaje claro si hay referencias (PROTECT).
"""
from django.db import migrations
from django.db.models.deletion import ProtectedError


ESTADOS = [
    ("borrador", "Borrador"),
    ("publicado", "Publicado"),
    ("retirado", "Retirado"),
]


def sembrar(apps, schema_editor):
    EstadoPublicacion = apps.get_model("catalogo", "EstadoPublicacion")
    for codigo, nombre in ESTADOS:
        EstadoPublicacion.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre}
        )


def deshacer(apps, schema_editor):
    EstadoPublicacion = apps.get_model("catalogo", "EstadoPublicacion")
    for codigo, _ in ESTADOS:
        try:
            EstadoPublicacion.objects.filter(codigo=codigo).delete()
        except ProtectedError as exc:
            tablas = sorted({obj._meta.db_table for obj in exc.protected_objects})
            raise RuntimeError(
                "No se pueden eliminar los estados de publicación: hay filas que "
                f"los referencian ({', '.join(tablas)}). Código: '{codigo}'. "
                "La FK usa PROTECT; vacíe o migre esas filas antes de revertir."
            ) from exc


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0008_estado_publicacion"),
    ]

    operations = [
        migrations.RunPython(sembrar, reverse_code=deshacer),
    ]
