# Vincula cada venta con su intento aprobado del mismo pedido (AZ-S1-19). Solo datos.
from django.db import migrations
from django.db.models import Count


def poblar(apps, schema_editor):
    Venta = apps.get_model("pagos", "Venta")
    IntentoPago = apps.get_model("pagos", "IntentoPago")
    db = schema_editor.connection.alias

    sin_aprobado = []
    ambiguos = []
    for venta in Venta.objects.using(db).all():
        aprobados = list(
            IntentoPago.objects.using(db)
            .filter(pedido_id=venta.pedido_id, estado_id="aprobado")
            .values_list("pk", flat=True)
        )
        if len(aprobados) == 0:
            sin_aprobado.append(venta.pedido_id)
        elif len(aprobados) > 1:
            ambiguos.append(venta.pedido_id)
        else:
            venta.intento_aprobado_id = aprobados[0]
            venta.save(update_fields=["intento_aprobado"])

    if sin_aprobado:
        raise RuntimeError(
            "Tabla 'pagos_venta', campo 'intento_aprobado': "
            f"{len(sin_aprobado)} venta(s) sin intento aprobado del mismo pedido "
            f"(pedido_id ejemplo: {sin_aprobado[0]})."
        )
    if ambiguos:
        raise RuntimeError(
            "Tabla 'pagos_venta', campo 'intento_aprobado': "
            f"{len(ambiguos)} venta(s) con más de un intento aprobado del mismo pedido "
            f"(pedido_id ejemplo: {ambiguos[0]})."
        )


def revertir(apps, schema_editor):
    Venta = apps.get_model("pagos", "Venta")
    Venta.objects.using(schema_editor.connection.alias).update(intento_aprobado=None)


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0016_venta_intento_nullable"),
    ]

    operations = [
        migrations.RunPython(poblar, revertir),
    ]
