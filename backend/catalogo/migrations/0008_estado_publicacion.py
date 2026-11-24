"""
Crea el catálogo de estados de publicación de oferta (AZ-S1-17).

Paso 1 (esquema): define ``EstadoPublicacion`` con código único estable.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0007_retirar_fks_categoria_genero"),
    ]

    operations = [
        migrations.CreateModel(
            name="EstadoPublicacion",
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
                "verbose_name": "Estado de publicación",
                "verbose_name_plural": "Estados de publicación",
                "ordering": ["codigo"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("codigo",),
                        name="catalogo_estadopublicacion_codigo_unico",
                    )
                ],
            },
        ),
    ]
