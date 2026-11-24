# Añade intento_aprobado nullable a Venta (AZ-S1-19). Solo esquema.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0015_guardia_reversion_onetoone"),
    ]

    operations = [
        migrations.AddField(
            model_name="venta",
            name="intento_aprobado",
            field=models.ForeignKey(
                blank=True,
                help_text="Intento de pago aprobado que originó la venta (trazabilidad protegida).",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="venta_generada",
                to="pagos.intentopago",
            ),
        ),
    ]
