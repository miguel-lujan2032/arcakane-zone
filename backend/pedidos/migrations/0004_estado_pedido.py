"""
Crea el catálogo de estados de pedido (AZ-S1-17).

Paso 1 (esquema): define ``EstadoPedido`` con código único estable. Solo
esquema, sin datos.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0003_integridad_detallepedido"),
    ]

    operations = [
        migrations.CreateModel(
            name="EstadoPedido",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "codigo",
                    models.CharField(
                        help_text="Identificador estable del estado; no es la etiqueta visible.",
                        max_length=50,
                    ),
                ),
                ("nombre", models.CharField(max_length=100)),
                ("descripcion", models.TextField(blank=True)),
            ],
            options={
                "verbose_name": "Estado de pedido",
                "verbose_name_plural": "Estados de pedido",
                "ordering": ["codigo"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("codigo",),
                        name="pedidos_estadopedido_codigo_unico",
                    )
                ],
            },
        ),
    ]
