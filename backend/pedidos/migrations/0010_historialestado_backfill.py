# Rellena una fila inicial de historial por pedido existente (AZ-S1-19). Solo datos.
from django.db import migrations

OBS = "Estado vigente al migrar (AZ-S1-19); historial previo no disponible"


def poblar(apps, schema_editor):
    Pedido = apps.get_model("pedidos", "Pedido")
    Historial = apps.get_model("pedidos", "HistorialEstadoPedido")
    db = schema_editor.connection.alias
    existentes = set(Historial.objects.using(db).values_list("pedido_id", flat=True))
    a_crear = []
    for p in Pedido.objects.using(db).all():
        if p.pk in existentes:
            continue
        a_crear.append(Historial(
            pedido_id=p.pk,
            estado_id=p.estado_id,
            fecha=p.actualizado_en,
            actor_id=None,
            observacion=OBS,
        ))
    if a_crear:
        Historial.objects.using(db).bulk_create(a_crear)
    # Verifica que ningún pedido quede sin historial.
    total = Pedido.objects.using(db).count()
    con_hist = Historial.objects.using(db).values("pedido_id").distinct().count()
    faltan = total - con_hist
    if faltan:
        raise RuntimeError(
            f"Tabla 'pedidos_historialestadopedido', campo 'pedido_id': "
            f"{faltan} fila(s) de pedido sin historial inicial tras la migración."
        )


def revertir(apps, schema_editor):
    Historial = apps.get_model("pedidos", "HistorialEstadoPedido")
    Historial.objects.using(schema_editor.connection.alias).filter(observacion=OBS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0009_historialestado_schema"),
    ]

    operations = [
        migrations.RunPython(poblar, revertir),
    ]
