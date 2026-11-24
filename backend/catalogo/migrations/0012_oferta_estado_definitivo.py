"""
Consolida la FK de estado de publicación y recrea los índices (AZ-S1-17).

Paso 5 (esquema): elimina ``estado_publicacion_legacy``, deja
``estado_publicacion`` como FK NOT NULL con default del catálogo y recrea los
dos índices compuestos con sus nombres originales.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0011_copiar_estado_publicacion"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="ofertavideojuego",
            name="estado_publicacion_legacy",
        ),
        migrations.AlterField(
            model_name="ofertavideojuego",
            name="estado_publicacion",
            field=models.ForeignKey(
                db_column="estado_publicacion",
                db_index=False,
                default="publicado",
                help_text="Estado editorial de la oferta (catálogo catalogo.EstadoPublicacion).",
                on_delete=django.db.models.deletion.PROTECT,
                related_name="ofertas",
                to="catalogo.estadopublicacion",
                to_field="codigo",
            ),
        ),
        migrations.AddIndex(
            model_name="ofertavideojuego",
            index=models.Index(
                fields=["estado_publicacion", "stock"],
                name="catalogo_oferta_est_stock_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="ofertavideojuego",
            index=models.Index(
                fields=["plataforma", "estado_publicacion"],
                name="catalogo_oferta_plat_est_idx",
            ),
        ),
    ]
