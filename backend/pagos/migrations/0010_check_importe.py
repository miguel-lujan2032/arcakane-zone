# Restaura el check de no negatividad sobre importe (AZ-S1-19). Solo esquema.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0009_rename_monto_importe"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="pago",
            constraint=models.CheckConstraint(
                condition=models.Q(importe__gte=0),
                name="pagos_intento_importe_nn",
            ),
        ),
    ]
