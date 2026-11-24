"""
Libro mayor de movimientos de inventario (AZ-S1-14): esquema inicial.

Crea los catálogos relacionales de tipos y motivos de movimiento y el
ledger ``MovimientoInventarioOfertaVideojuego`` (inmutable, con saldos
corridos congelados, idempotencia por clave única y trazabilidad al
detalle de pedido). Ver ``inventario/models.py`` para la estrategia
completa y el ADR ``docs/adr_az-s1-14-libro-mayor-inventario.md``.
"""
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('catalogo', '0002_ofertavideojuego'),
        ('pedidos', '0002_detallepedido_oferta'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MotivoMovimientoInventario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(help_text='Identificador estable del motivo (p. ej. VENTA).', max_length=50)),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField(blank=True)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Motivo de movimiento de inventario',
                'verbose_name_plural': 'Motivos de movimiento de inventario',
                'ordering': ['codigo'],
                'constraints': [models.UniqueConstraint(fields=('codigo',), name='inventario_motivomovimiento_codigo_unico')],
            },
        ),
        migrations.CreateModel(
            name='TipoMovimientoInventario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(help_text='Identificador estable del tipo (p. ej. ENTRADA, SALIDA).', max_length=50)),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField(blank=True)),
                ('naturaleza', models.CharField(choices=[('entrada', 'Entrada'), ('salida', 'Salida'), ('ajuste', 'Ajuste')], max_length=10)),
                ('activo', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Tipo de movimiento de inventario',
                'verbose_name_plural': 'Tipos de movimiento de inventario',
                'ordering': ['codigo'],
                'constraints': [models.UniqueConstraint(fields=('codigo',), name='inventario_tipomovimiento_codigo_unico')],
            },
        ),
        migrations.CreateModel(
            name='MovimientoInventarioOfertaVideojuego',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('observacion', models.TextField(blank=True)),
                ('cantidad', models.PositiveIntegerField()),
                ('unidad', models.CharField(default='unidad', max_length=50)),
                ('saldo_anterior', models.PositiveIntegerField()),
                ('saldo_posterior', models.PositiveIntegerField()),
                ('fecha_hora', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('clave_idempotencia', models.CharField(max_length=200)),
                ('detalle_pedido', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='movimiento_inventario', to='pedidos.detallepedido')),
                ('motivo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='movimientos', to='inventario.motivomovimientoinventario')),
                ('movimiento_compensado', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='movimientos_compensatorios', to='inventario.movimientoinventarioofertavideojuego')),
                ('oferta', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimientos_inventario', to='catalogo.ofertavideojuego')),
                ('usuario_responsable', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='movimientos_inventario', to=settings.AUTH_USER_MODEL)),
                ('tipo_movimiento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimientos', to='inventario.tipomovimientoinventario')),
            ],
            options={
                'verbose_name': 'Movimiento de inventario de oferta',
                'verbose_name_plural': 'Movimientos de inventario de ofertas',
                'ordering': ['fecha_hora', 'pk'],
                'indexes': [models.Index(fields=['oferta', '-fecha_hora'], name='inventario_oferta_fecha_idx'), models.Index(fields=['tipo_movimiento', '-fecha_hora'], name='inventario_mov_tipo_fecha_idx')],
                'constraints': [models.UniqueConstraint(fields=('clave_idempotencia',), name='inventario_movimiento_clave_idempotencia_unica'), models.UniqueConstraint(condition=models.Q(('detalle_pedido__isnull', False)), fields=('detalle_pedido',), name='inventario_movimiento_detalle_pedido_unico'), models.CheckConstraint(condition=models.Q(('cantidad__gt', 0)), name='inventario_movimiento_cantidad_positiva'), models.CheckConstraint(condition=models.Q(('saldo_anterior__gte', 0)), name='inventario_movimiento_saldo_anterior_no_negativo'), models.CheckConstraint(condition=models.Q(('saldo_posterior__gte', 0)), name='inventario_movimiento_saldo_posterior_no_negativo')],
            },
        ),
    ]
