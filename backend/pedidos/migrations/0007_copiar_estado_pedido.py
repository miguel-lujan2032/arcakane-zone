"""
Copia los estados actuales de pedido a la FK del catálogo (AZ-S1-17).

Paso 4 (datos): valida que cada valor existente tenga equivalente en el
catálogo y lo copia. Aborta con tabla, campo, valor desconocido y cantidad de
filas si hay datos fuera del dominio. La reversión restaura ``estado_legacy``
antes de que el esquema vuelva a NOT NULL.
"""
from django.db import migrations
from django.db.models import Count, F, Q


HISTORICOS = {"pendiente", "pagado", "cancelado"}


def copiar(apps, schema_editor):
    Pedido = apps.get_model("pedidos", "Pedido")
    EstadoPedido = apps.get_model("pedidos", "EstadoPedido")
    codigos = list(EstadoPedido.objects.values_list("codigo", flat=True))

    invalidos = (
        Pedido.objects.filter(
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
            "Migración pedidos.0007 abortada: la tabla 'pedidos_pedido', campo "
            "'estado', contiene valores sin equivalente en "
            f"'pedidos_estadopedido.codigo': {detalle}. "
            "Corrija los datos y vuelva a aplicar la migración."
        )

    for codigo in codigos:
        Pedido.objects.filter(estado_legacy=codigo).update(estado=codigo)


def copiar_atras(apps, schema_editor):
    Pedido = apps.get_model("pedidos", "Pedido")

    invalidos = (
        Pedido.objects.filter(Q(estado__isnull=True) | ~Q(estado__in=HISTORICOS))
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
            "Reversión de pedidos.0007 abortada: la tabla 'pedidos_pedido', "
            "campo 'estado', contiene códigos sin equivalente en el esquema "
            f"anterior: {detalle}. "
            "Migre o elimine esas filas antes de revertir."
        )

    Pedido.objects.update(estado_legacy=F("estado"))


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0006_pedido_estado_fk"),
    ]

    operations = [
        migrations.RunPython(copiar, reverse_code=copiar_atras),
    ]
