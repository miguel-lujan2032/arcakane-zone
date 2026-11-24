# Endurece referencia/actualizado_en y añade unicidades de intento (AZ-S1-19). Solo esquema.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0013_intentopago_datos_backfill"),
    ]

    operations = [
        migrations.AlterField(
            model_name="intentopago",
            name="referencia",
            field=models.CharField(
                help_text="Referencia interna única del intento (identidad trazable).",
                max_length=100,
            ),
        ),
        migrations.AlterField(
            model_name="intentopago",
            name="actualizado_en",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddConstraint(
            model_name="intentopago",
            constraint=models.UniqueConstraint(
                fields=("referencia",),
                name="pagos_intento_ref_unico",
            ),
        ),
        migrations.AddConstraint(
            model_name="intentopago",
            constraint=models.UniqueConstraint(
                condition=models.Q(("clave_idempotencia", ""), _negated=True),
                fields=("clave_idempotencia",),
                name="pagos_intento_idem_unico",
            ),
        ),
    ]
