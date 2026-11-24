"""
Agrega la FK de estado de publicación a la oferta (AZ-S1-17).

Paso 3 (esquema): retira los índices compuestos que dependen del campo,
renombra ``estado_publicacion`` a ``estado_publicacion_legacy``, lo relaja a
NULL y agrega la FK nueva (nullable, sin índice propio) conservando el nombre
de columna ``estado_publicacion``.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0009_semilla_estados_publicacion"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="ofertavideojuego",
            name="catalogo_oferta_est_stock_idx",
        ),
        migrations.RemoveIndex(
            model_name="ofertavideojuego",
            name="catalogo_oferta_plat_est_idx",
        ),
        migrations.RenameField(
            model_name="ofertavideojuego",
            old_name="estado_publicacion",
            new_name="estado_publicacion_legacy",
        ),
        migrations.AlterField(
            model_name="ofertavideojuego",
            name="estado_publicacion_legacy",
            field=models.CharField(
                max_length=20, null=True, blank=True, default="publicado"
            ),
        ),
        migrations.AddField(
            model_name="ofertavideojuego",
            name="estado_publicacion",
            field=models.ForeignKey(
                db_column="estado_publicacion",
                db_index=False,
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ofertas",
                to="catalogo.estadopublicacion",
                to_field="codigo",
            ),
        ),
    ]
