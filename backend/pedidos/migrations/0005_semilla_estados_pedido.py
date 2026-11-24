"""
Siembra idempotente del catálogo de estados de pedido (AZ-S1-17).

Paso 2 (datos): inserta los códigos estables. El reverso falla con un mensaje
claro si hay filas que referencian el catálogo (PROTECT).
"""
from django.db import migrations
from django.db.models.deletion import ProtectedError


ESTADOS = [
    ("pendiente", "Pendiente"),
    ("pagado", "Pagado"),
    ("cancelado", "Cancelado"),
]


def sembrar(apps, schema_editor):
    EstadoPedido = apps.get_model("pedidos", "EstadoPedido")
    for codigo, nombre in ESTADOS:
        EstadoPedido.objects.get_or_create(codigo=codigo, defaults={"nombre": nombre})


def deshacer(apps, schema_editor):
    EstadoPedido = apps.get_model("pedidos", "EstadoPedido")
    for codigo, _ in ESTADOS:
        try:
            EstadoPedido.objects.filter(codigo=codigo).delete()
        except ProtectedError as exc:
            tablas = sorted({obj._meta.db_table for obj in exc.protected_objects})
            raise RuntimeError(
                "No se pueden eliminar los estados de pedido: hay filas que los "
                f"referencian ({', '.join(tablas)}). Código: '{codigo}'. "
                "La FK usa PROTECT; vacíe o migre esas filas antes de revertir."
            ) from exc


class Migration(migrations.Migration):

    dependencies = [
        ("pedidos", "0004_estado_pedido"),
    ]

    operations = [
        migrations.RunPython(sembrar, reverse_code=deshacer),
    ]
