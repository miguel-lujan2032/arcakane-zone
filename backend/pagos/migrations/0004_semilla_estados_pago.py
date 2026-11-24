"""
Siembra idempotente del catálogo de estados de intento de pago (AZ-S1-17).

Paso 2 (datos). El reverso falla con mensaje claro si hay referencias (PROTECT).
"""
from django.db import migrations
from django.db.models.deletion import ProtectedError


ESTADOS = [
    ("aprobado", "Aprobado"),
    ("rechazado", "Rechazado"),
    ("pendiente", "Pendiente"),
]


def sembrar(apps, schema_editor):
    EstadoIntentoPago = apps.get_model("pagos", "EstadoIntentoPago")
    for codigo, nombre in ESTADOS:
        EstadoIntentoPago.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre}
        )


def deshacer(apps, schema_editor):
    EstadoIntentoPago = apps.get_model("pagos", "EstadoIntentoPago")
    for codigo, _ in ESTADOS:
        try:
            EstadoIntentoPago.objects.filter(codigo=codigo).delete()
        except ProtectedError as exc:
            tablas = sorted({obj._meta.db_table for obj in exc.protected_objects})
            raise RuntimeError(
                "No se pueden eliminar los estados de intento de pago: hay filas "
                f"que los referencian ({', '.join(tablas)}). Código: '{codigo}'. "
                "La FK usa PROTECT; vacíe o migre esas filas antes de revertir."
            ) from exc


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0003_estado_intento_pago"),
    ]

    operations = [
        migrations.RunPython(sembrar, reverse_code=deshacer),
    ]
