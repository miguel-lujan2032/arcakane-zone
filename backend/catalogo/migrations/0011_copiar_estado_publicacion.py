"""
Copia los estados de publicación actuales a la FK del catálogo (AZ-S1-17).

Paso 4 (datos): valida y copia. Aborta con tabla, campo, valor desconocido y
cantidad de filas si hay datos fuera del dominio. La reversión restaura
``estado_publicacion_legacy`` antes de volver a NOT NULL.
"""
from django.db import migrations
from django.db.models import Count, F, Q


HISTORICOS = {"borrador", "publicado", "retirado"}


def copiar(apps, schema_editor):
    Oferta = apps.get_model("catalogo", "OfertaVideojuego")
    EstadoPublicacion = apps.get_model("catalogo", "EstadoPublicacion")
    codigos = list(EstadoPublicacion.objects.values_list("codigo", flat=True))

    invalidos = (
        Oferta.objects.filter(
            Q(estado_publicacion_legacy__isnull=True)
            | ~Q(estado_publicacion_legacy__in=codigos)
        )
        .values("estado_publicacion_legacy")
        .annotate(total=Count("id"))
        .order_by("estado_publicacion_legacy")
    )
    if invalidos:
        detalle = ", ".join(
            f"NULL ({r['total']} filas)"
            if r["estado_publicacion_legacy"] is None
            else f"'{r['estado_publicacion_legacy']}' ({r['total']} filas)"
            for r in invalidos
        )
        raise RuntimeError(
            "Migración catalogo.0011 abortada: la tabla "
            "'catalogo_ofertavideojuego', campo 'estado_publicacion', contiene "
            "valores sin equivalente en 'catalogo_estadopublicacion.codigo': "
            f"{detalle}. Corrija los datos y vuelva a aplicar la migración."
        )

    for codigo in codigos:
        Oferta.objects.filter(estado_publicacion_legacy=codigo).update(
            estado_publicacion=codigo
        )


def copiar_atras(apps, schema_editor):
    Oferta = apps.get_model("catalogo", "OfertaVideojuego")

    invalidos = (
        Oferta.objects.filter(
            Q(estado_publicacion__isnull=True)
            | ~Q(estado_publicacion__in=HISTORICOS)
        )
        .values("estado_publicacion")
        .annotate(total=Count("id"))
        .order_by("estado_publicacion")
    )
    if invalidos:
        detalle = ", ".join(
            f"NULL ({r['total']} filas)"
            if r["estado_publicacion"] is None
            else f"'{r['estado_publicacion']}' ({r['total']} filas)"
            for r in invalidos
        )
        raise RuntimeError(
            "Reversión de catalogo.0011 abortada: la tabla "
            "'catalogo_ofertavideojuego', campo 'estado_publicacion', contiene "
            "códigos sin equivalente en el esquema anterior: "
            f"{detalle}. Migre o elimine esas filas antes de revertir."
        )

    Oferta.objects.update(estado_publicacion_legacy=F("estado_publicacion"))


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0010_oferta_estado_fk"),
    ]

    operations = [
        migrations.RunPython(copiar, reverse_code=copiar_atras),
    ]
