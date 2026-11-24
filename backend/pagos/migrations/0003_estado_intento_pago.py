"""
Crea el catálogo de estados de intento de pago (AZ-S1-17).

Paso 1 (esquema): define ``EstadoIntentoPago`` con código único estable.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0002_integridad_pagos"),
    ]

    operations = [
        migrations.CreateModel(
            name="EstadoIntentoPago",
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
                "verbose_name": "Estado de intento de pago",
                "verbose_name_plural": "Estados de intento de pago",
                "ordering": ["codigo"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("codigo",),
                        name="pagos_estadointentopago_codigo_unico",
                    )
                ],
            },
        ),
    ]
