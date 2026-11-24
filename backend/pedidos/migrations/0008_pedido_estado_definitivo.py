"""
Consolida la FK de estado del pedido y retira el campo antiguo (AZ-S1-17).

Paso 5 (esquema): elimina ``estado_legacy`` y deja ``estado`` como FK NOT
NULL con el default del catálogo. El reverso reintroduce ``estado_legacy``
nullable antes de restaurar datos (el paso 4 inverso los copia).
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0007_copiar_estado_pedido"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="pedido",
            name="estado_legacy",
        ),
        migrations.AlterField(
            model_name="pedido",
            name="estado",
            field=models.ForeignKey(
                db_column="estado",
                db_index=False,
                default="pendiente",
                help_text="Estado actual del pedido (catálogo pedidos.EstadoPedido).",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pedidos",
                to="pedidos.estadopedido",
                to_field="codigo",
            ),
        ),
    ]
