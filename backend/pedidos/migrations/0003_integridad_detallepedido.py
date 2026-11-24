"""
Integridad de las líneas de pedido (AZ-S1-15).

Antes de crear los ``CheckConstraint`` se validan los datos existentes. Si
alguna fila viola las nuevas reglas la migración ABORTA con un error
descriptivo (tabla, campo y cantidad de filas afectadas); no se normaliza
ningún dato en silencio. El operador debe corregir las filas y reintentar.

Reglas incorporadas:
  - ``cantidad >= 1``: una línea representa al menos una unidad.
  - ``precio_unitario >= 0``: el precio congelado nunca es negativo.
"""
from django.db import migrations, models


def validar_datos_para_checks(apps, schema_editor):
    """Aborta si hay filas que violarían los checks de DetallePedido."""
    DetallePedido = apps.get_model("pedidos", "DetallePedido")
    problemas = []

    cantidad_invalida = DetallePedido.objects.filter(cantidad__lt=1).count()
    if cantidad_invalida:
        problemas.append(
            "tabla 'pedidos_detallepedido', campo 'cantidad': "
            f"{cantidad_invalida} fila(s) con cantidad < 1"
        )

    precio_negativo = DetallePedido.objects.filter(
        precio_unitario__lt=0
    ).count()
    if precio_negativo:
        problemas.append(
            "tabla 'pedidos_detallepedido', campo 'precio_unitario': "
            f"{precio_negativo} fila(s) con valor negativo"
        )

    if problemas:
        raise RuntimeError(
            "Migración pedidos.0003 abortada: existen datos que violan las "
            "nuevas restricciones de integridad. Corríjalos y vuelva a "
            "ejecutar la migración:\n- " + "\n- ".join(problemas)
        )


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0003_indices_catalogo"),
        ("pedidos", "0002_detallepedido_oferta"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="pedido",
            index=models.Index(
                fields=["cliente", "-creado_en"],
                name="pedidos_pedido_cli_fecha_idx",
            ),
        ),
        # La validación de datos va ANTES de agregar los checks.
        migrations.RunPython(
            validar_datos_para_checks,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="detallepedido",
            constraint=models.CheckConstraint(
                condition=models.Q(cantidad__gte=1),
                name="pedidos_detallepedido_cantidad_positiva",
            ),
        ),
        migrations.AddConstraint(
            model_name="detallepedido",
            constraint=models.CheckConstraint(
                condition=models.Q(precio_unitario__gte=0),
                name="pedidos_detallepedido_precio_unitario_no_negativo",
            ),
        ),
    ]
