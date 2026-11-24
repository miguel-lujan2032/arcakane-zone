"""
Agrega la FK de estado al pedido sin eliminar el valor antiguo (AZ-S1-17).

Paso 3 (esquema): renombra ``estado`` a ``estado_legacy``, lo relaja a NULL
para permitir la reversión y agrega la FK nueva (nullable, sin índice propio)
que conserva el nombre de columna ``estado``.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0005_semilla_estados_pedido"),
    ]

    operations = [
        migrations.RenameField(
            model_name="pedido",
            old_name="estado",
            new_name="estado_legacy",
        ),
        migrations.AlterField(
            model_name="pedido",
            name="estado_legacy",
            field=models.CharField(
                max_length=20, null=True, blank=True, default="pendiente"
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="estado",
            field=models.ForeignKey(
                db_column="estado",
                db_index=False,
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pedidos",
                to="pedidos.estadopedido",
                to_field="codigo",
            ),
        ),
    ]
