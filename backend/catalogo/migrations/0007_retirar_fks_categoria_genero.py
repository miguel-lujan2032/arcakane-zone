"""
Retira las FKs directas de categoría/género y expone el M2M (AZ-S1-16).

Orden de operaciones:
  1. Elimina los índices de AZ-S1-15 que dependían de las columnas retiradas.
  2. Elimina las columnas ``categoria_id`` y ``genero_id`` de ``Videojuego``.
  3. Añade los ManyToManyField ``categorias`` y ``generos`` con ``through``,
     que reutilizan las tablas puente creadas en 0004.

Los datos ya fueron copiados en 0006, por lo que no se pierde ninguna
asociación. Al revertir, las columnas vuelven a crearse como NULL y 0006 se
encarga de rellenarlas con la primera asociación antes de que 0005 restaure
``NOT NULL``. No modifica datos: solo el esquema.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0006_copiar_asociaciones_catalogo"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="videojuego",
            name="catalogo_vj_cat_activo_idx",
        ),
        migrations.RemoveIndex(
            model_name="videojuego",
            name="catalogo_vj_gen_activo_idx",
        ),
        migrations.RemoveField(
            model_name="videojuego",
            name="categoria",
        ),
        migrations.RemoveField(
            model_name="videojuego",
            name="genero",
        ),
        migrations.AddField(
            model_name="videojuego",
            name="categorias",
            field=models.ManyToManyField(
                blank=True,
                related_name="videojuegos",
                through="catalogo.VideojuegoCategoria",
                to="catalogo.categoria",
            ),
        ),
        migrations.AddField(
            model_name="videojuego",
            name="generos",
            field=models.ManyToManyField(
                blank=True,
                related_name="videojuegos",
                through="catalogo.VideojuegoGenero",
                to="catalogo.genero",
            ),
        ),
    ]
