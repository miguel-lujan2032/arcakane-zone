# Endurece el identificador estable de rol (AZ-S1-18).
# Paso 3 (esquema): codigo NOT NULL + UniqueConstraint nombrado. Separado de la
# población de datos (0003) para evitar mezclar esquema y datos.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0003_poblar_codigo_roles"),
    ]

    operations = [
        migrations.AlterField(
            model_name="rol",
            name="codigo",
            field=models.CharField(
                max_length=50,
                help_text="Identificador estable del rol; no es la etiqueta visible.",
            ),
        ),
        migrations.AddConstraint(
            model_name="rol",
            constraint=models.UniqueConstraint(
                fields=("codigo",),
                name="cuentas_rol_codigo_unico",
            ),
        ),
    ]
