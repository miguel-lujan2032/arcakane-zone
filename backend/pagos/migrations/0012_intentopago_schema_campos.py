# Convierte pedido a FK (1:N), añade campos e índices de IntentoPago (AZ-S1-19). Solo esquema.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0011_rename_model_intento"),
    ]

    operations = [
        migrations.AlterField(
            model_name="intentopago",
            name="pedido",
            field=models.ForeignKey(
                help_text="Pedido al que pertenece el intento (permite varios intentos).",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="intentos_pago",
                to="pedidos.pedido",
            ),
        ),
        migrations.AlterField(
            model_name="intentopago",
            name="estado",
            field=models.ForeignKey(
                db_column="estado",
                db_index=False,
                default="pendiente",
                help_text="Resultado del intento de pago (catálogo pagos.EstadoIntentoPago).",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="intentos_pago",
                to="pagos.estadointentopago",
                to_field="codigo",
            ),
        ),
        migrations.AlterField(
            model_name="intentopago",
            name="importe",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Importe del intento (snapshot monetario del intento).",
                max_digits=10,
            ),
        ),
        migrations.AddField(
            model_name="intentopago",
            name="clave_idempotencia",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Clave de idempotencia del intento; única cuando está presente.",
                max_length=200,
            ),
        ),
        migrations.AddField(
            model_name="intentopago",
            name="actualizado_en",
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddIndex(
            model_name="intentopago",
            index=models.Index(fields=["pedido", "-creado_en"], name="pagos_intento_ped_fec_idx"),
        ),
        migrations.AddIndex(
            model_name="intentopago",
            index=models.Index(fields=["estado", "-creado_en"], name="pagos_intento_est_fec_idx"),
        ),
    ]
