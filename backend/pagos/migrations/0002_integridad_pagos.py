"""
Integridad de pagos y ventas (AZ-S1-15).

Antes de crear los ``CheckConstraint`` se validan los datos existentes. Si
alguna fila viola las nuevas reglas la migración ABORTA con un error
descriptivo (tabla, campo y cantidad de filas afectadas); no se normaliza
ningún dato en silencio. El operador debe corregir las filas y reintentar.

Reglas incorporadas:
  - ``Pago.monto >= 0``.
  - ``Venta.total >= 0``.

Además agrega el índice de reportes de ventas por fecha de registro.
"""
from django.db import migrations, models


def validar_datos_para_checks(apps, schema_editor):
    """Aborta si hay importes negativos en pagos o ventas."""
    Pago = apps.get_model("pagos", "Pago")
    Venta = apps.get_model("pagos", "Venta")
    problemas = []

    montos_negativos = Pago.objects.filter(monto__lt=0).count()
    if montos_negativos:
        problemas.append(
            "tabla 'pagos_pago', campo 'monto': "
            f"{montos_negativos} fila(s) con valor negativo"
        )

    totales_negativos = Venta.objects.filter(total__lt=0).count()
    if totales_negativos:
        problemas.append(
            "tabla 'pagos_venta', campo 'total': "
            f"{totales_negativos} fila(s) con valor negativo"
        )

    if problemas:
        raise RuntimeError(
            "Migración pagos.0002 abortada: existen datos que violan las "
            "nuevas restricciones de integridad. Corríjalos y vuelva a "
            "ejecutar la migración:\n- " + "\n- ".join(problemas)
        )


class Migration(migrations.Migration):

    dependencies = [
        ("pagos", "0001_initial"),
        ("pedidos", "0003_integridad_detallepedido"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="venta",
            index=models.Index(
                fields=["registrada_en"],
                name="pagos_venta_registrada_idx",
            ),
        ),
        # La validación de datos va ANTES de agregar los checks.
        migrations.RunPython(
            validar_datos_para_checks,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name="pago",
            constraint=models.CheckConstraint(
                condition=models.Q(monto__gte=0),
                name="pagos_pago_monto_no_negativo",
            ),
        ),
        migrations.AddConstraint(
            model_name="venta",
            constraint=models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name="pagos_venta_total_no_negativo",
            ),
        ),
    ]
