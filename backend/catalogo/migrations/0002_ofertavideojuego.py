"""
Normaliza el catálogo comercial (AZ-S1-13).

Crea la oferta de videojuego (unidad vendible videojuego + plataforma),
traslada precio/stock desde Videojuego a la oferta y elimina la relación
directa videojuego→plataforma.

Reversibilidad: precio, stock y plataforma se relajan a ``null=True`` antes
de eliminarse para que la reversión pueda re-agregarlas como columnas
opcionales, repoblarlas desde las ofertas (``RunPython`` de retorno) y
restaurar después la restricción NOT NULL. Queda como caso de intervención
manual únicamente un videojuego sin ofertas, que no tendría plataforma que
restaurar (FK NOT NULL en el esquema legacy).
"""
import django.db.models.deletion
from django.db import migrations, models


def crear_ofertas_desde_videojuegos(apps, schema_editor):
    """Traslada precio, stock y plataforma de cada videojuego a su oferta."""
    Videojuego = apps.get_model("catalogo", "Videojuego")
    OfertaVideojuego = apps.get_model("catalogo", "OfertaVideojuego")

    for vj in Videojuego.objects.all().select_related("plataforma"):
        OfertaVideojuego.objects.update_or_create(
            videojuego=vj,
            plataforma=vj.plataforma,
            defaults={
                "sku": f"AZ-{vj.pk:04d}-{vj.plataforma_id:03d}",
                "precio_vigente": vj.precio,
                "stock": vj.stock,
                # Se preserva la visibilidad comercial previa del título.
                "estado_publicacion": "publicado" if vj.activo else "retirado",
            },
        )


def restaurar_videojuegos_desde_ofertas(apps, schema_editor):
    """Reversión: devuelve precio/stock/plataforma desde la primera oferta del título."""
    Videojuego = apps.get_model("catalogo", "Videojuego")

    for vj in Videojuego.objects.all():
        oferta = vj.ofertas.order_by("pk").first()
        if oferta is None:
            continue
        vj.precio = oferta.precio_vigente
        vj.stock = oferta.stock
        vj.plataforma_id = oferta.plataforma_id
        vj.save()


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="OfertaVideojuego",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("precio_vigente", models.DecimalField(decimal_places=2, max_digits=10)),
                ("sku", models.CharField(max_length=50, unique=True)),
                ("stock", models.PositiveIntegerField(default=0)),
                ("estado_publicacion", models.CharField(choices=[("borrador", "Borrador"), ("publicado", "Publicado"), ("retirado", "Retirado")], default="publicado", max_length=20)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("plataforma", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ofertas", to="catalogo.plataforma")),
                ("videojuego", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ofertas", to="catalogo.videojuego")),
            ],
            options={
                "verbose_name": "Oferta de videojuego",
                "verbose_name_plural": "Ofertas de videojuegos",
                "ordering": ["videojuego__titulo", "plataforma__nombre"],
                "constraints": [
                    models.UniqueConstraint(fields=["videojuego", "plataforma"], name="catalogo_ofertavideojuego_videojuego_plataforma_unicos"),
                    models.CheckConstraint(condition=models.Q(precio_vigente__gte=0), name="catalogo_ofertavideojuego_precio_vigente_no_negativo"),
                ],
                "indexes": [models.Index(fields=["estado_publicacion"], name="catalogo_oferta_estado_idx")],
            },
        ),
        # Relajar las columnas legacy a opcionales ANTES de eliminarlas:
        # la reversión las re-agrega sin default obligatorio, las repuebla
        # desde las ofertas y restaura aquí el NOT NULL.
        migrations.AlterField(
            model_name="videojuego",
            name="precio",
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name="videojuego",
            name="stock",
            field=models.PositiveIntegerField(default=0, null=True),
        ),
        migrations.AlterField(
            model_name="videojuego",
            name="plataforma",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="videojuegos", to="catalogo.plataforma"),
        ),
        migrations.RunPython(crear_ofertas_desde_videojuegos, restaurar_videojuegos_desde_ofertas),
        migrations.RemoveField(model_name="videojuego", name="precio"),
        migrations.RemoveField(model_name="videojuego", name="stock"),
        migrations.RemoveField(model_name="videojuego", name="plataforma"),
    ]
