"""
Tablas puente explícitas para categorías y géneros (AZ-S1-16).

Solo crea esquema: las tablas ``catalogo_videojuegocategoria`` y
``catalogo_videojuegogenero`` con sus FKs, la unicidad de cada pareja y los
índices de consulta inversa. No toca los datos ni las FKs directas de
``Videojuego``; esa responsabilidad queda repartida en las migraciones
siguientes para no mezclar DDL y DML en PostgreSQL.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0003_indices_catalogo"),
    ]

    operations = [
        migrations.CreateModel(
            name="VideojuegoCategoria",
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
                    "categoria",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="vinculos_videojuego",
                        to="catalogo.categoria",
                    ),
                ),
                (
                    "videojuego",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vinculos_categoria",
                        to="catalogo.videojuego",
                    ),
                ),
            ],
            options={
                "verbose_name": "Categoría del videojuego",
                "verbose_name_plural": "Categorías del videojuego",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("videojuego", "categoria"),
                        name="catalogo_videojuegocategoria_videojuego_categoria_unicos",
                    )
                ],
                "indexes": [
                    models.Index(
                        fields=["categoria", "videojuego"],
                        name="catalogo_vjc_categoria_idx",
                    )
                ],
            },
        ),
        migrations.CreateModel(
            name="VideojuegoGenero",
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
                    "genero",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="vinculos_videojuego",
                        to="catalogo.genero",
                    ),
                ),
                (
                    "videojuego",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vinculos_genero",
                        to="catalogo.videojuego",
                    ),
                ),
            ],
            options={
                "verbose_name": "Género del videojuego",
                "verbose_name_plural": "Géneros del videojuego",
                "constraints": [
                    models.UniqueConstraint(
                        fields=("videojuego", "genero"),
                        name="catalogo_videojuegogenero_videojuego_genero_unicos",
                    )
                ],
                "indexes": [
                    models.Index(
                        fields=["genero", "videojuego"],
                        name="catalogo_vjg_genero_idx",
                    )
                ],
            },
        ),
    ]
