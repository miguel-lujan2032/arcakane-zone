# Retira la FK directa de rol y añade la relación M2M explícita (AZ-S1-18).
# Paso 6 (esquema): RemoveField Usuario.rol y DESPUÉS AddField ManyToManyField
# roles (through=UsuarioRol, related_name="usuarios", blank=True) para evitar
# choque de related_name. La reversión con varios roles pierde asignaciones
# adicionales (la FK monovaluada solo conserva una, según 0006 reverso).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0006_copiar_roles_usuario"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="usuario",
            name="rol",
        ),
        migrations.AddField(
            model_name="usuario",
            name="roles",
            field=models.ManyToManyField(
                blank=True,
                related_name="usuarios",
                through="cuentas.UsuarioRol",
                to="cuentas.rol",
            ),
        ),
    ]
