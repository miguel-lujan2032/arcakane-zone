"""
Agrega la FK de estado al pago sin eliminar el valor antiguo (AZ-S1-17).

Paso 3 (esquema): renombra ``estado`` a ``estado_legacy``, lo relaja a NULL y
agrega la FK nueva (nullable, sin índice propio) con ``db_column='estado'``.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0004_semilla_estados_pago"),
    ]

    operations = [
        migrations.RenameField(
            model_name="pago",
            old_name="estado",
            new_name="estado_legacy",
        ),
        migrations.AlterField(
            model_name="pago",
            name="estado_legacy",
            field=models.CharField(
                max_length=20, null=True, blank=True, default="pendiente"
            ),
        ),
        migrations.AddField(
            model_name="pago",
            name="estado",
            field=models.ForeignKey(
                db_column="estado",
                db_index=False,
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="pagos",
                to="pagos.estadointentopago",
                to_field="codigo",
            ),
        ),
    ]
