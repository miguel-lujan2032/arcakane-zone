# Elimina el check de monto antes de renombrar el campo (AZ-S1-19). Solo esquema.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0007_pago_estado_definitivo"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="pago",
            name="pagos_pago_monto_no_negativo",
        ),
    ]
