# Crea la tabla puente explícita usuario↔rol (AZ-S1-18).
# Paso 4 (esquema): UsuarioRol con UniqueConstraint(usuario, rol) e índice
# rol→usuarios (usuario→roles lo cubre el UniqueConstraint). Sin metadatos de
# auditoría; si se añade asignado_por en el futuro hará falta through_fields.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0004_rol_codigo_definitivo"),
    ]

    operations = [
        migrations.CreateModel(
            name="UsuarioRol",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "rol",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="asignaciones_rol",
                        to="cuentas.rol",
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="asignaciones_rol",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Asignación de rol",
                "verbose_name_plural": "Asignaciones de rol",
            },
        ),
        migrations.AddConstraint(
            model_name="usuariorol",
            constraint=models.UniqueConstraint(
                fields=("usuario", "rol"),
                name="cuentas_usuariorol_usuario_rol_unico",
            ),
        ),
        migrations.AddIndex(
            model_name="usuariorol",
            index=models.Index(
                fields=["rol"],
                name="cuentas_urol_rol_idx",
            ),
        ),
    ]
