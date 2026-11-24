"""
Crea los catálogos maestros y sus tablas puente (AZ-S1-20).

Paso 1 (esquema): ``Desarrolladora``, ``Distribuidora``, ``ClasificacionEdad``
e ``Idioma``; las puentes ``VideojuegoDesarrolladora``,
``VideojuegoDistribuidora`` y ``VideojuegoIdioma``; los M2M de ``Videojuego``
y la FK nullable ``clasificacion_edad`` por ``to_field="codigo"``. Solo DDL:
la siembra de datos de referencia vive en ``0014``.
"""

import django.db.models.deletion
import django.db.models.functions.text
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo', '0012_oferta_estado_definitivo'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClasificacionEdad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(help_text='Código PEGI: 3, 7, 12, 16 o 18.', max_length=20)),
                ('nombre', models.CharField(max_length=50)),
                ('orden', models.PositiveSmallIntegerField(help_text='Orden de presentación; menor primero.')),
            ],
            options={
                'verbose_name': 'Clasificación por edad',
                'verbose_name_plural': 'Clasificaciones por edad',
                'ordering': ['orden', 'codigo'],
                'constraints': [models.UniqueConstraint(fields=('codigo',), name='catalogo_clasificacionedad_codigo_unico'), models.UniqueConstraint(fields=('nombre',), name='catalogo_clasificacionedad_nombre_unico')],
            },
        ),
        migrations.AddField(
            model_name='videojuego',
            name='clasificacion_edad',
            field=models.ForeignKey(blank=True, db_column='clasificacion_edad', db_index=False, help_text='Clasificación PEGI; NULL si se desconoce.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='videojuegos', to='catalogo.clasificacionedad', to_field='codigo'),
        ),
        migrations.CreateModel(
            name='Desarrolladora',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(help_text='Identificador estable (slug); no es la etiqueta visible.', max_length=100)),
                ('nombre', models.CharField(max_length=150)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Desarrolladora',
                'verbose_name_plural': 'Desarrolladoras',
                'ordering': ['nombre'],
                'constraints': [models.UniqueConstraint(fields=('codigo',), name='catalogo_desarrolladora_codigo_unico'), models.UniqueConstraint(django.db.models.functions.text.Lower('nombre'), name='catalogo_desarrolladora_nombre_unico')],
            },
        ),
        migrations.CreateModel(
            name='Distribuidora',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(help_text='Identificador estable (slug); no es la etiqueta visible.', max_length=100)),
                ('nombre', models.CharField(max_length=150)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Distribuidora',
                'verbose_name_plural': 'Distribuidoras',
                'ordering': ['nombre'],
                'constraints': [models.UniqueConstraint(fields=('codigo',), name='catalogo_distribuidora_codigo_unico'), models.UniqueConstraint(django.db.models.functions.text.Lower('nombre'), name='catalogo_distribuidora_nombre_unico')],
            },
        ),
        migrations.CreateModel(
            name='Idioma',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(help_text='Código ISO 639-1 de dos letras (es, en, fr...).', max_length=2)),
                ('nombre', models.CharField(max_length=100)),
            ],
            options={
                'verbose_name': 'Idioma',
                'verbose_name_plural': 'Idiomas',
                'ordering': ['nombre'],
                'constraints': [models.UniqueConstraint(fields=('codigo',), name='catalogo_idioma_codigo_unico'), models.UniqueConstraint(django.db.models.functions.text.Lower('nombre'), name='catalogo_idioma_nombre_unico')],
            },
        ),
        migrations.CreateModel(
            name='VideojuegoDesarrolladora',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('desarrolladora', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='vinculos_videojuego', to='catalogo.desarrolladora')),
                ('videojuego', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vinculos_desarrolladora', to='catalogo.videojuego')),
            ],
            options={
                'verbose_name': 'Desarrolladora del videojuego',
                'verbose_name_plural': 'Desarrolladoras del videojuego',
            },
        ),
        migrations.AddField(
            model_name='videojuego',
            name='desarrolladoras',
            field=models.ManyToManyField(blank=True, related_name='videojuegos', through='catalogo.VideojuegoDesarrolladora', to='catalogo.desarrolladora'),
        ),
        migrations.CreateModel(
            name='VideojuegoDistribuidora',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('distribuidora', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='vinculos_videojuego', to='catalogo.distribuidora')),
                ('videojuego', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vinculos_distribuidora', to='catalogo.videojuego')),
            ],
            options={
                'verbose_name': 'Distribuidora del videojuego',
                'verbose_name_plural': 'Distribuidoras del videojuego',
            },
        ),
        migrations.AddField(
            model_name='videojuego',
            name='distribuidoras',
            field=models.ManyToManyField(blank=True, related_name='videojuegos', through='catalogo.VideojuegoDistribuidora', to='catalogo.distribuidora'),
        ),
        migrations.CreateModel(
            name='VideojuegoIdioma',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('audio', 'Audio'), ('interfaz', 'Interfaz'), ('subtitulos', 'Subtítulos')], max_length=10)),
                ('idioma', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='vinculos_videojuego', to='catalogo.idioma')),
                ('videojuego', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vinculos_idioma', to='catalogo.videojuego')),
            ],
            options={
                'verbose_name': 'Idioma del videojuego',
                'verbose_name_plural': 'Idiomas del videojuego',
            },
        ),
        migrations.AddField(
            model_name='videojuego',
            name='idiomas',
            field=models.ManyToManyField(blank=True, related_name='videojuegos', through='catalogo.VideojuegoIdioma', to='catalogo.idioma'),
        ),
        migrations.AddIndex(
            model_name='videojuego',
            index=models.Index(fields=['clasificacion_edad'], name='catalogo_vj_clasificacion_idx'),
        ),
        migrations.AddIndex(
            model_name='videojuegodesarrolladora',
            index=models.Index(fields=['desarrolladora', 'videojuego'], name='catalogo_vjd_desarroll_idx'),
        ),
        migrations.AddConstraint(
            model_name='videojuegodesarrolladora',
            constraint=models.UniqueConstraint(fields=('videojuego', 'desarrolladora'), name='catalogo_vjdesarrolladora_unicos'),
        ),
        migrations.AddIndex(
            model_name='videojuegodistribuidora',
            index=models.Index(fields=['distribuidora', 'videojuego'], name='catalogo_vjd_distrib_idx'),
        ),
        migrations.AddConstraint(
            model_name='videojuegodistribuidora',
            constraint=models.UniqueConstraint(fields=('videojuego', 'distribuidora'), name='catalogo_vjdistribuidora_unicos'),
        ),
        migrations.AddIndex(
            model_name='videojuegoidioma',
            index=models.Index(fields=['idioma', 'tipo', 'videojuego'], name='catalogo_vji_idioma_tipo_idx'),
        ),
        migrations.AddConstraint(
            model_name='videojuegoidioma',
            constraint=models.UniqueConstraint(fields=('videojuego', 'idioma', 'tipo'), name='catalogo_vjidioma_tipo_unicos'),
        ),
        migrations.AddConstraint(
            model_name='videojuegoidioma',
            constraint=models.CheckConstraint(condition=models.Q(('tipo__in', ['audio', 'interfaz', 'subtitulos'])), name='catalogo_vji_tipo_valido'),
        ),
    ]
