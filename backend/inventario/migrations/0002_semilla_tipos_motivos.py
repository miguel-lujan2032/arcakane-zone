"""
Semilla idempotente del catálogo de tipos y motivos de movimiento (AZ-S1-14).

Usa ``get_or_create`` por ``codigo``: puede ejecutarse sobre una base ya
sembrada sin duplicar filas y sin sobrescribir ediciones posteriores.

La reversión elimina las filas sembradas; si ya existen movimientos del
ledger que las referencian falla con ``ProtectedError``: el libro mayor
manda sobre el catálogo y el historial nunca se sacrifica al revertir.
"""
from django.db import migrations

TIPOS = [
    ("ENTRADA", "Entrada", "Ingreso de unidades al inventario de la oferta", "entrada"),
    ("SALIDA", "Salida", "Salida de unidades del inventario de la oferta", "salida"),
    ("AJUSTE", "Ajuste", "Fijación del saldo por conteo o corrección", "ajuste"),
]

MOTIVOS = [
    ("VENTA", "Venta", "Salida generada por la compra de un cliente"),
    ("DEVOLUCION", "Devolución", "Reingreso de unidades devueltas por un cliente"),
    ("AJUSTE_FISICO", "Ajuste físico", "Corrección del saldo tras un conteo de inventario"),
    ("CARGA_INICIAL", "Carga inicial", "Existencias iniciales al crear la oferta"),
]


def sembrar_catalogos(apps, schema_editor):
    TipoMovimiento = apps.get_model("inventario", "TipoMovimientoInventario")
    MotivoMovimiento = apps.get_model("inventario", "MotivoMovimientoInventario")

    for codigo, nombre, descripcion, naturaleza in TIPOS:
        TipoMovimiento.objects.get_or_create(
            codigo=codigo,
            defaults={
                "nombre": nombre,
                "descripcion": descripcion,
                "naturaleza": naturaleza,
            },
        )
    for codigo, nombre, descripcion in MOTIVOS:
        MotivoMovimiento.objects.get_or_create(
            codigo=codigo,
            defaults={"nombre": nombre, "descripcion": descripcion},
        )


def retirar_catalogos_sembrados(apps, schema_editor):
    TipoMovimiento = apps.get_model("inventario", "TipoMovimientoInventario")
    MotivoMovimiento = apps.get_model("inventario", "MotivoMovimientoInventario")

    TipoMovimiento.objects.filter(codigo__in=[t[0] for t in TIPOS]).delete()
    MotivoMovimiento.objects.filter(codigo__in=[m[0] for m in MOTIVOS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(sembrar_catalogos, retirar_catalogos_sembrados),
    ]
