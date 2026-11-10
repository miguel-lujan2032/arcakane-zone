# ADR — AZ-S1-14: Libro mayor de movimientos de inventario

**Estado:** aceptado · **Issue:** #16 · **Alcance:** solo capa de datos
(modelos, migraciones, constraints, índices y pruebas).

## Contexto

El inventario se administra a nivel de la **unidad comercial vendible** — la
`OfertaVideojuego` (app `catalogo`), no el videojuego genérico. Hasta ahora el
único estado de inventario era `OfertaVideojuego.stock`, un contador sin
historial: imposible auditar cómo llegó a su valor actual, quién movió qué,
ni reconciliar una venta con su salida de existencias.

## Decisión

Crear la app **`inventario`** con tres modelos — un modelo por concepto — y
sin lógica de orquestación: los modelos solo garantizan invariantes de
integridad; la lógica que escribe el ledger es de servicios (otro issue).

### Estrategia de ledger: saldos corridos congelados por movimiento

Cada `MovimientoInventarioOfertaVideojuego` registra la cantidad operada y el
saldo de la oferta **antes** y **después** de aplicarla (running balances
congelados). El historial de una oferta es verificable punto a punto sin
recalcular nada, y el último movimiento siempre expone el saldo vigente:

```text
saldo_anterior(n) = saldo_posterior(n-1)     (continuidad de la cadena)
saldo vigente     = saldo_posterior(último)
```

El efecto sobre el saldo se deriva de la **naturaleza** del tipo (dato de la
fila de catálogo):

| naturaleza | efecto aritmético            | ejemplo                 |
|------------|-------------------------------|-------------------------|
| `entrada`  | `saldo_posterior = saldo_anterior + cantidad` | compra a proveedor |
| `salida`   | `saldo_posterior = saldo_anterior - cantidad` | venta, merma       |
| `ajuste`   | `saldo_posterior = cantidad` (el conteo fija el saldo) | conteo físico |

### Catálogos relacionales, no enums

`TipoMovimientoInventario` (código único + `naturaleza`) y
`MotivoMovimientoInventario` son tablas. Agregar un tipo o motivo nuevo es
insertar una fila — sin cambios de código ni de esquema (abierto/cerrado).
El texto libre no controlado va en `observacion` del movimiento.

La `naturaleza` sí es `CharField` + `TextChoices` **dentro de la fila del
catálogo**: es el dominio cerrado de la derivación aritmética (3 valores
estables), no un catálogo de negocio.

### Inmutabilidad total vía ORM

El ledger es solo-apéndice. `ModeloInmutable` (base abstracta) bloquea
`save()` sobre instancias existentes y `delete()` de instancia;
`QuerySetInmutable` (manager por defecto, heredado también por los related
managers, p. ej. `oferta.movimientos_inventario`) bloquea `update()`,
`bulk_update()` y `delete()` de queryset. Todo ello lanza
`RegistroInmutableError`. Las correcciones son **movimientos compensatorios
nuevos** que referencian al original (`movimiento_compensado`).

Excepción legítima: el flush de `TransactionTestCase` usa `DELETE` crudo que
bypassa el ORM — el contrato aplica a operaciones ordinarias, no al harness.

### Dependencias hacia adentro

Todas las FK usan referencias por cadena: `catalogo.OfertaVideojuego`,
`pedidos.DetallePedido`, `settings.AUTH_USER_MODEL` y `"self"`. El módulo no
importa modelos concretos de otras apps (inversión de dependencias) y todas
son `PROTECT` — el historial manda: no se borra una oferta, catálogo,
usuario autor, detalle origen o movimiento compensado que tenga movimientos.

### Constraints (nombres explícitos, ≤ 30 chars por índice)

| Constraint | Regla |
|---|---|
| `inventario_tipomovimiento_codigo_unico` | código de tipo único |
| `inventario_motivomovimiento_codigo_unico` | código de motivo único |
| `inventario_movimiento_clave_idempotencia_unica` | idempotencia por clave única |
| `inventario_movimiento_detalle_pedido_unico` | `detalle_pedido` único condicional (`isnull=False`); null repetido permitido |
| `inventario_movimiento_cantidad_positiva` | `cantidad > 0` |
| `inventario_movimiento_saldo_anterior_no_negativo` | `saldo_anterior >= 0` |
| `inventario_movimiento_saldo_posterior_no_negativo` | `saldo_posterior >= 0` |

### Índices

| Índice | Justificación |
|---|---|
| `inventario_oferta_fecha_idx` (`oferta`, `-fecha_hora`) | historial de una oferta del más reciente al más antiguo — la consulta del issue |
| `inventario_mov_tipo_fecha_idx` (`tipo_movimiento`, `-fecha_hora`) | consultas operativas por tipo (p. ej. "salidas recientes", conciliación de ventas) |

Ambos verificados con `EXPLAIN QUERY PLAN` en las pruebas.

### Migraciones

- `0001_initial`: esquema (catálogos, ledger, constraints, índices).
- `0002_semilla_tipos_motivos`: semilla idempotente (`get_or_create` por
  código). Tipos: ENTRADA/SALIDA/AJUSTE. Motivos: VENTA, DEVOLUCION,
  AJUSTE_FISICO, CARGA_INICIAL. Su reverso elimina las filas sembradas y
  falla con `ProtectedError` si el ledger ya las referencia.

## Limitaciones conocidas (y su mitigación)

1. **La relación aritmética `saldo_posterior = saldo_anterior ± cantidad` no
   es expresable como `CheckConstraint`**: el signo vive en la fila del
   catálogo (`tipo_movimiento.naturaleza`) y los check constraints solo
   pueden referirse a columnas de la propia fila. La garantizan los
   servicios bajo el contrato de abajo; los invariantes que la BD sí
   asegura son los de la tabla anterior.
2. **Doble capa de `>= 0` en los saldos del ledger**: los campos son
   `PositiveIntegerField` (que en DDL de SQLite ya emite `CHECK >= 0`) y
   además llevan `CheckConstraint` explícito: el implícito no está
   garantizado entre backends; el explícito documenta la regla de negocio y
   es portable. Para `OfertaVideojuego.stock` (preexistente, fuera del
   alcance de este issue) no se añadió constraint nuevo por la misma razón:
   su `PositiveIntegerField` ya lo impone.
3. **`select_for_update()` es no-op en SQLite** (tests): el locking real se
   ejerce en PostgreSQL. Por eso los tests de concurrencia configuran
   `transaction_mode: IMMEDIATE` en `settings_test.py` — `BEGIN IMMEDIATE`
   serializa a los escritores en la BD en memoria compartida y hace
   deterministas las carreras.
4. **`unidad` es un `CharField` con default `"unidad"`**: no existe catálogo
   de unidades en el repo; si aparece, se promueve a FK.

## Contrato para el issue de servicios (pendiente)

Todo servicio que escriba el ledger DEBE:

```python
with transaction.atomic():
    oferta = OfertaVideojuego.objects.select_for_update().get(pk=...)
    saldo = oferta.stock
    # derivar saldo_posterior según tipo_movimiento.naturaleza y validar
    # la aritmética (continuidad de la cadena) ANTES de insertar
    MovimientoInventarioOfertaVideojuego.objects.create(
        oferta=oferta, ..., saldo_anterior=saldo, saldo_posterior=...,
        clave_idempotencia=...,  # único por operación de negocio
    )
    oferta.stock = saldo_posterior
    oferta.save(update_fields=["stock"])
```

Queda pendiente para ese issue: los casos de uso (entrada por compra,
salida por venta con `detalle_pedido`, ajuste por conteo, compensaciones),
la generación de la `clave_idempotencia`, el admin de los catálogos y la
presentación del historial.
