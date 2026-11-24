# Agrega el identificador estable de rol (AZ-S1-18).
# Paso 1 (esquema): añade "codigo" nullable y sin unique para permitir poblarlo
# en un paso de datos separado (PostgreSQL: esquema y datos no se mezclan).
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="rol",
            name="codigo",
            field=models.CharField(
                max_length=50,
                null=True,
                blank=True,
                help_text="Identificador estable del rol; no es la etiqueta visible.",
            ),
        ),
    ]
