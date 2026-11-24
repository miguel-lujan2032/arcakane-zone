"""
Relaja las FKs directas de ``Videojuego`` antes de retirarlas (AZ-S1-16).

Las columnas ``categoria_id`` y ``genero_id`` pasan a admitir NULL. Es un paso
intermedio necesario para que la reversión pueda recrear las columnas vacías y
rellenarlas después desde las tablas puente, sin violar ``NOT NULL``.

No modifica datos: solo el esquema.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0004_tablas_puente_categoria_genero"),
    ]

    operations = [
        migrations.AlterField(
            model_name="videojuego",
            name="categoria",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="videojuegos",
                to="catalogo.categoria",
            ),
        ),
        migrations.AlterField(
            model_name="videojuego",
            name="genero",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="videojuegos",
                to="catalogo.genero",
            ),
        ),
    ]
