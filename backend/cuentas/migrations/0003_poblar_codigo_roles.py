# Puebla el código estable de los roles y garantiza los roles base (AZ-S1-18).
# Paso 2 (datos): mapeo explícito desde nombre; get_or_create idempotente de
# cliente/administrador. Aborta con RuntimeError (tabla, campo, valor, cantidad
# de filas) ante nombres sin mapeo o colisiones.
from django.db import migrations


ROLES_BASE = {
    "cliente": "Cliente",
    "administrador": "Administrador",
}
MAPEO_NOMBRE_A_CODIGO = {
    "cliente": "cliente",
    "administrador": "administrador",
}


def poblar_codigo(apps, schema_editor):
    Rol = apps.get_model("cuentas", "Rol")
    db_table = Rol._meta.db_table

    existentes = list(Rol.objects.all())
    codigos_asignados = {}

    for rol in existentes:
        nombre_norm = (rol.nombre or "").strip().lower()
        codigo = MAPEO_NOMBRE_A_CODIGO.get(nombre_norm)
        if codigo is None:
            raise RuntimeError(
                f"Tabla '{db_table}', campo 'nombre': valor '{rol.nombre}' sin "
                "mapeo a código estable (1 fila). Corrija el nombre o defina su "
                "mapeo antes de migrar."
            )
        if codigo in codigos_asignados and codigos_asignados[codigo] != rol.pk:
            raise RuntimeError(
                f"Tabla '{db_table}', campo 'codigo': valor '{codigo}' colisiona "
                "entre roles existentes (2 filas o más). Corrija los nombres "
                "duplicados antes de migrar."
            )
        codigos_asignados[codigo] = rol.pk
        rol.codigo = codigo
        rol.save(update_fields=["codigo"])

    # Garantiza los roles base de forma idempotente.
    for codigo, nombre in ROLES_BASE.items():
        Rol.objects.get_or_create(
            codigo=codigo, defaults={"nombre": nombre, "activo": True}
        )


def revertir_poblar(apps, schema_editor):
    Rol = apps.get_model("cuentas", "Rol")
    # Limpia el código (el esquema lo volverá nullable al revertir 0004/0002).
    Rol.objects.update(codigo=None)


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0002_rol_codigo_nullable"),
    ]

    operations = [
        migrations.RunPython(poblar_codigo, revertir_poblar),
    ]
