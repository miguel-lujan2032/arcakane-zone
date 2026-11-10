"""
DetallePedido pasa a referenciar la oferta adquirida (AZ-S1-13).

- Reasigna cada línea histórica a la oferta de su videojuego.
- Congela título y plataforma como snapshot transaccional y conserva
  el precio unitario histórico.
- La unicidad de línea pasa a ser (pedido, oferta).

Reversibilidad: la FK legacy ``videojuego`` se relaja a ``null=True`` antes
de eliminarse para que la reversión pueda re-agregarla como columna opcional,
repoblarla desde la oferta (``RunPython`` de retorno) y restaurar después la
restricción NOT NULL y la unicidad (pedido, videojuego) del esquema legacy.
Requiere intervención manual solo si un pedido tiene dos ofertas del mismo
videojuego, combinación que el esquema legacy no puede representar.
"""
import django.db.models.deletion
from django.db import migrations, models


def reasignar_detalles_a_ofertas(apps, schema_editor):
    """Apunta cada detalle a la oferta creada para su videojuego y congela snapshots."""
    DetallePedido = apps.get_model("pedidos", "DetallePedido")
    OfertaVideojuego = apps.get_model("catalogo", "OfertaVideojuego")

    for detalle in DetallePedido.objects.select_related("videojuego").all():
        # Tras catalogo.0002 cada videojuego tiene exactamente una oferta.
        oferta = OfertaVideojuego.objects.filter(
            videojuego_id=detalle.videojuego_id
        ).first()
        if oferta is None:
            continue
        detalle.oferta = oferta
        detalle.titulo_snapshot = detalle.videojuego.titulo
        detalle.plataforma_snapshot = oferta.plataforma.nombre
        detalle.save()


def desasignar_detalles_de_ofertas(apps, schema_editor):
    """Reversión: restablece la referencia directa al videojuego."""
    DetallePedido = apps.get_model("pedidos", "DetallePedido")

    for detalle in DetallePedido.objects.select_related("oferta").all():
        detalle.videojuego = detalle.oferta.videojuego
        detalle.save()


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0002_ofertavideojuego"),
        ("pedidos", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="detallepedido",
            name="oferta",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="detalles_pedido", to="catalogo.ofertavideojuego"),
        ),
        migrations.AddField(
            model_name="detallepedido",
            name="titulo_snapshot",
            field=models.CharField(max_length=200, null=True),
        ),
        migrations.AddField(
            model_name="detallepedido",
            name="plataforma_snapshot",
            field=models.CharField(max_length=100, null=True),
        ),
        # Relajar la FK legacy a opcional ANTES de eliminarla: la reversión
        # la re-agrega sin default, la repuebla desde la oferta y restaura
        # aquí el NOT NULL del esquema legacy.
        migrations.AlterField(
            model_name="detallepedido",
            name="videojuego",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="detalles_pedido", to="catalogo.videojuego"),
        ),
        migrations.RunPython(reasignar_detalles_a_ofertas, desasignar_detalles_de_ofertas),
        migrations.AlterField(
            model_name="detallepedido",
            name="oferta",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="detalles_pedido", to="catalogo.ofertavideojuego"),
        ),
        migrations.AlterField(
            model_name="detallepedido",
            name="titulo_snapshot",
            field=models.CharField(max_length=200),
        ),
        migrations.AlterField(
            model_name="detallepedido",
            name="plataforma_snapshot",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterUniqueTogether(name="detallepedido", unique_together=None),
        migrations.AddConstraint(
            model_name="detallepedido",
            constraint=models.UniqueConstraint(fields=["pedido", "oferta"], name="pedidos_detallepedido_pedido_oferta_unicos"),
        ),
        migrations.RemoveField(model_name="detallepedido", name="videojuego"),
    ]
