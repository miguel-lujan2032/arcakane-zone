# Copia el rol directo de cada usuario a la tabla puente (AZ-S1-18).
# Paso 5 (datos): crea la asignación inicial por cada Usuario.rol no nulo
# (idempotente); usuarios sin rol quedan sin asignación.
# Reverso: restaura Usuario.rol según decisión 8 (administrador si existe; si
# no, el de menor PK de asignación). Pérdida al revertir: si un usuario tiene
# varios roles, solo se conserva uno en la FK monovaluada y se pierden los demás.
from django.db import migrations


def copiar_roles(apps, schema_editor):
    Usuario = apps.get_model("cuentas", "Usuario")
    UsuarioRol = apps.get_model("cuentas", "UsuarioRol")

    for usuario in Usuario.objects.exclude(rol__isnull=True):
        UsuarioRol.objects.get_or_create(usuario_id=usuario.pk, rol_id=usuario.rol_id)


def restaurar_rol_directo(apps, schema_editor):
    Usuario = apps.get_model("cuentas", "Usuario")
    UsuarioRol = apps.get_model("cuentas", "UsuarioRol")
    Rol = apps.get_model("cuentas", "Rol")

    for usuario in Usuario.objects.all():
        asignaciones = list(
            UsuarioRol.objects.filter(usuario_id=usuario.pk).order_by("pk")
        )
        if not asignaciones:
            usuario.rol_id = None
            usuario.save(update_fields=["rol"])
            continue

        rol_admin = (
            Rol.objects.filter(codigo="administrador")
            .values_list("pk", flat=True)
            .first()
        )
        elegido = None
        if rol_admin is not None:
            for a in asignaciones:
                if a.rol_id == rol_admin:
                    elegido = a
                    break
        if elegido is None:
            elegido = asignaciones[0]  # menor PK de asignación
        usuario.rol_id = elegido.rol_id
        usuario.save(update_fields=["rol"])
        # Nota: las asignaciones adicionales (si las hay) no pueden representarse
        # en la FK monovaluada y se pierden al revertir a 0001.


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0005_usuariorol_puente"),
    ]

    operations = [
        migrations.RunPython(copiar_roles, restaurar_rol_directo),
    ]
