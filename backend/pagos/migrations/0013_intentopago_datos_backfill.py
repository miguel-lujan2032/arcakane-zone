# Backfill de referencia/actualizado_en y validación de duplicados (AZ-S1-19). Solo datos.
from django.db import migrations
from django.db.models import Count


def poblar(apps, schema_editor):
    IntentoPago = apps.get_model("pagos", "IntentoPago")
    db = schema_editor.connection.alias

    # Aborta ante referencias no vacías duplicadas (no se normaliza en silencio).
    duplicadas = (
        IntentoPago.objects.using(db)
        .exclude(referencia="")
        .values("referencia")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )
    if duplicadas.exists():
        r = duplicadas.order_by("referencia").first()
        raise RuntimeError(
            "Tabla 'pagos_intentopago', campo 'referencia': valor "
            f"'{r['referencia']}' duplicado en {r['total']} fila(s). "
            "Corrija los datos antes de migrar."
        )

    # Relleno determinístico para referencias históricas vacías.
    for intento in IntentoPago.objects.using(db).filter(referencia=""):
        intento.referencia = f"LEGACY-{intento.pk}"
        if intento.actualizado_en is None:
            intento.actualizado_en = intento.creado_en
        intento.save(update_fields=["referencia", "actualizado_en"])

    # Asegura actualizado_en en filas restantes.
    for intento in IntentoPago.objects.using(db).filter(actualizado_en__isnull=True):
        intento.actualizado_en = intento.creado_en
        intento.save(update_fields=["actualizado_en"])


def revertir(apps, schema_editor):
    IntentoPago = apps.get_model("pagos", "IntentoPago")
    db = schema_editor.connection.alias
    # Restaura referencias generadas por migración antes de relajar constraints.
    IntentoPago.objects.using(db).filter(referencia__startswith="LEGACY-").update(referencia="")


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0012_intentopago_schema_campos"),
    ]

    operations = [
        migrations.RunPython(poblar, revertir),
    ]
