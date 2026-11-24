# Renombra monto a importe en el intento de pago (AZ-S1-19). Solo esquema.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0008_remove_check_monto"),
    ]

    operations = [
        migrations.RenameField(
            model_name="pago",
            old_name="monto",
            new_name="importe",
        ),
    ]
