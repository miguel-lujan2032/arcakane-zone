"""
Índices de consulta del catálogo (AZ-S1-15).

Sustituye el índice de una sola columna ``(estado_publicacion)`` por el
compuesto ``(estado_publicacion, stock)`` que cubre el filtro del storefront
(publicadas con stock), y agrega los índices de las consultas por plataforma
y por categoría/género activos.

Solo cambia índices: no altera datos ni restricciones de integridad.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0002_ofertavideojuego"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="ofertavideojuego",
            name="catalogo_oferta_estado_idx",
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
        migrations.AddIndex(
            model_name="videojuego",
            index=models.Index(
                fields=["categoria", "activo"],
                name="catalogo_vj_cat_activo_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="videojuego",
            index=models.Index(
                fields=["genero", "activo"],
                name="catalogo_vj_gen_activo_idx",
            ),
        ),
    ]
