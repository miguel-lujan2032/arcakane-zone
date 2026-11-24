# Guardia de reversión OneToOne←FK: aborta si hay >1 intento por pedido (AZ-S1-19). Solo datos.
from django.db import migrations
from django.db.models import Count


def noop(apps, schema_editor):
    pass


def verificar_reversion(apps, schema_editor):
    IntentoPago = apps.get_model("pagos", "IntentoPago")
    db = schema_editor.connection.alias
    conflictos = (
        IntentoPago.objects.using(db)
        .values("pedido_id")
        .annotate(total=Count("id"))
        .filter(total__gt=1)
    )
    if conflictos.exists():
        cantidad = conflictos.count()
        ejemplo = conflictos.order_by("pedido_id").first()["pedido_id"]
        raise RuntimeError(
            "Tabla 'pagos_intentopago', campo 'pedido_id': "
            f"{cantidad} pedido(s) con más de un intento (ej. pedido_id={ejemplo}). "
            "No es posible revertir OneToOne←FK sin pérdida; resuelva manualmente "
            "conservando un solo intento por pedido antes de revertir."
        )


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0014_intentopago_constraints"),
    ]

    operations = [
        migrations.RunPython(noop, verificar_reversion),
    ]
