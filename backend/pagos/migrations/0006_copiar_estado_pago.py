"""
Copia los estados actuales de pago a la FK del catálogo (AZ-S1-17).

Paso 4 (datos): valida y copia. Aborta con tabla, campo, valor desconocido y
cantidad de filas si hay datos fuera del dominio. La reversión restaura
``estado_legacy`` antes de volver a NOT NULL.
"""
from django.db import migrations
from django.db.models import Count, F, Q


HISTORICOS = {"aprobado", "rechazado", "pendiente"}


def copiar(apps, schema_editor):
    Pago = apps.get_model("pagos", "Pago")
    EstadoIntentoPago = apps.get_model("pagos", "EstadoIntentoPago")
    codigos = list(EstadoIntentoPago.objects.values_list("codigo", flat=True))

    invalidos = (
        Pago.objects.filter(
            Q(estado_legacy__isnull=True) | ~Q(estado_legacy__in=codigos)
        )
        .values("estado_legacy")
        .annotate(total=Count("id"))
        .order_by("estado_legacy")
    )
    if invalidos:
        detalle = ", ".join(
            f"NULL ({r['total']} filas)"
            if r["estado_legacy"] is None
            else f"'{r['estado_legacy']}' ({r['total']} filas)"
            for r in invalidos
        )
        raise RuntimeError(
            "Migración pagos.0006 abortada: la tabla 'pagos_pago', campo "
            "'estado', contiene valores sin equivalente en "
            f"'pagos_estadointentopago.codigo': {detalle}. "
            "Corrija los datos y vuelva a aplicar la migración."
        )

    for codigo in codigos:
        Pago.objects.filter(estado_legacy=codigo).update(estado=codigo)


def copiar_atras(apps, schema_editor):
    Pago = apps.get_model("pagos", "Pago")

    invalidos = (
        Pago.objects.filter(Q(estado__isnull=True) | ~Q(estado__in=HISTORICOS))
        .values("estado")
        .annotate(total=Count("id"))
        .order_by("estado")
    )
    if invalidos:
        detalle = ", ".join(
            f"NULL ({r['total']} filas)"
            if r["estado"] is None
            else f"'{r['estado']}' ({r['total']} filas)"
            for r in invalidos
        )
        raise RuntimeError(
            "Reversión de pagos.0006 abortada: la tabla 'pagos_pago', campo "
            "'estado', contiene códigos sin equivalente en el esquema anterior: "
            f"{detalle}. Migre o elimine esas filas antes de revertir."
        )

    Pago.objects.update(estado_legacy=F("estado"))


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0005_pago_estado_fk"),
    ]

    operations = [
        migrations.RunPython(copiar, reverse_code=copiar_atras),
    ]
