# Endurece intento_aprobado en Venta: NOT NULL y único (AZ-S1-19). Solo esquema.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0017_venta_intento_backfill"),
    ]

    operations = [
        migrations.AlterField(
            model_name="venta",
            name="intento_aprobado",
            field=models.OneToOneField(
                help_text="Intento de pago aprobado que originó la venta (trazabilidad protegida).",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="venta_generada",
                to="pagos.intentopago",
            ),
        ),
    ]
