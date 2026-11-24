# Crea el historial inmutable de estados de pedido (AZ-S1-19). Solo esquema.
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0008_pedido_estado_definitivo"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="HistorialEstadoPedido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateTimeField(default=django.utils.timezone.now, editable=False, help_text="Momento del registro del estado.")),
                ("observacion", models.TextField(blank=True, help_text="Observación o motivo asociado al registro.")),
                ("actor", models.ForeignKey(blank=True, help_text="Usuario responsable; NULL si fue el sistema o una migración.", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="cambios_estado_pedido", to=settings.AUTH_USER_MODEL)),
                ("estado", models.ForeignKey(db_column="estado", db_index=False, help_text="Estado del pedido en este registro histórico (catálogo).", on_delete=django.db.models.deletion.PROTECT, related_name="historial_pedidos", to="pedidos.estadopedido", to_field="codigo")),
                ("pedido", models.ForeignKey(help_text="Pedido cuyo cambio de estado se registra.", on_delete=django.db.models.deletion.PROTECT, related_name="historial_estados", to="pedidos.pedido")),
            ],
            options={
                "verbose_name": "Historial de estado de pedido",
                "verbose_name_plural": "Historial de estados de pedido",
                "ordering": ["fecha", "pk"],
            },
        ),
        migrations.AddIndex(
            model_name="historialestadopedido",
            index=models.Index(fields=["pedido", "fecha"], name="pedidos_hist_ped_fec_idx"),
        ),
    ]
