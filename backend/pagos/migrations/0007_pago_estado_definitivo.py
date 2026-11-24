"""
Consolida la FK de estado del pago y retira el campo antiguo (AZ-S1-17).

Paso 5 (esquema): elimina ``estado_legacy`` y deja ``estado`` como FK NOT
NULL con default del catálogo.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0006_copiar_estado_pago"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="pago",
            name="estado_legacy",
        ),
        migrations.AlterField(
            model_name="pago",
            name="estado",
            field=models.ForeignKey(
                db_column="estado",
                db_index=False,
                default="pendiente",
                help_text="Resultado del intento de pago (catálogo pagos.EstadoIntentoPago).",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pagos",
                to="pagos.estadointentopago",
                to_field="codigo",
            ),
        ),
    ]
