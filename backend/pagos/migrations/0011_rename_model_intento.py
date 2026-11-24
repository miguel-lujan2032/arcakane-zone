# Renombra el modelo Pago a IntentoPago (tabla pasa a pagos_intentopago) (AZ-S1-19). Solo esquema.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0010_check_importe"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Pago",
            new_name="IntentoPago",
        ),
        migrations.AlterModelOptions(
            name="intentopago",
            options={
                "verbose_name": "Intento de pago",
                "verbose_name_plural": "Intentos de pago",
            },
        ),
    ]
