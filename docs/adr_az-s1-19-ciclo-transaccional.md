# ADR AZ-S1-19 — Ciclo transaccional: historial de pedido, intentos de pago y venta aprobada

**Estado:** aceptado  
**Fecha:** 2026-11-16  
**Issue:** AZ-S1-19 «Normalizar ciclo transaccional: historial de estados de pedido, intentos de pago y venta aprobada»  
**Alcance:** solo capa de datos (modelos, migraciones, pruebas, documentación) con cambios mínimos autorizados en `backend/pagos/admin.py` y `backend/pagos/services.py`.

## Contexto

El esquema anterior modelaba el pago como `pagos.Pago` 1:1 con `Pedido` (`OneToOne`), sin historial de estados de pedido, sin trazabilidad estructural del intento que originaba la venta y con deudas de identidad/idempotencia (`referencia` no obligatoria ni única, `monto` sin semántica de intento). Un rechazo bloqueaba reintentos por la unicidad 1:1 y no existía una tabla de historial inmutable de estados.

## Decisión

### 1. Modelo relacional

- **`IntentoPago`** (antes `Pago`, tabla `pagos_intentopago`): 1:N con `Pedido` (`FK`, `PROTECT`, `related_name=intentos_pago`). Campos: `importe` (`Decimal(10,2)`, `>= 0`, snapshot), `estado` (FK a `EstadoIntentoPago` por `codigo`, `PROTECT`), `referencia` (única y obligatoria), `clave_idempotencia` (única condicional cuando no está vacía), `creado_en`, `actualizado_en`. Índices `pagos_intento_ped_fec_idx` `(pedido,-creado_en)` y `pagos_intento_est_fec_idx` `(estado,-creado_en)`.
- **`HistorialEstadoPedido`** (nuevo, `pedidos_historialestadopedido`): registro inmutable (hereda de `inventario.models.ModeloInmutable`) con `pedido` (FK `PROTECT`), `estado` (FK `EstadoPedido` por `codigo`, `PROTECT`), `fecha`, `actor` (FK a usuario, `PROTECT`, nullable) y `observacion`. Índice `pedidos_hist_ped_fec_idx` `(pedido,fecha)`.
- **`Venta`**: 1:1 con `Pedido` y 1:1 con `IntentoPago` mediante `intento_aprobado` (`OneToOne`, `PROTECT`, `related_name=venta_generada`). `total` se mantiene como **snapshot contable** (verificable contra la suma de `DetallePedido.subtotal`/`precio_unitario*cantidad` al momento de la venta). Una venta por pedido y un intento origina como máximo una venta.
- **Compatibilidad:** propiedad de solo lectura `Pedido.pago` que devuelve el intento aprobado del pedido (o `None`), para no tocar templates/vistas fuera de alcance.

### 2. Identidad e idempotencia de intentos

- `referencia`: única y obligatoria (`pagos_intento_ref_unico`). Históricos con referencia vacía se rellenan de forma determinística (`LEGACY-<pk>`); duplicados no vacíos provocan abortar la migración con `RuntimeError` descriptivo (tabla, campo, valor, cantidad), sin normalización silenciosa.
- `clave_idempotencia`: campo separado, única condicional (`pagos_intento_idem_unico`) que permite valores vacíos repetidos. La aplicación de idempotencia en servicios es deuda técnica.

### 3. Integridad, borrado e inmutabilidad

- Políticas de borrado: todo `PROTECT` (pedido, estado, actor, intento, venta, referencias de historial) salvo `DetallePedido.pedido` `CASCADE` existente (se mantiene y se documenta).
- `HistorialEstadoPedido` es inmutable a nivel ORM (update/delete/bulk delete bloqueados) y el pedido con historial no puede borrarse (`PROTECT`).
- No se definen campos de tarjetas, CVV, PAN/CVC ni credenciales financieras.

### 4. Qué garantiza la base de datos y qué no

- **Garantiza:** relaciones 1:N pedido→intentos, FKs válidas a catálogos/pedido/actor, unicidad de `referencia` y de `clave_idempotencia` informada, `importe >= 0`, 1:1 pedido↔venta y 1:1 intento↔venta, preservación del historial y protección frente a borrado de referencias usadas.
- **No garantiza por sí sola:** que `Venta.intento_aprobado` pertenezca al mismo `pedido` de la venta, ni que el intento vinculado esté en estado `aprobado`. Estas coherencias se cubren con pruebas y quedan para el futuro issue de servicios/checkout (no implementado en esta capa). `Venta.total` es snapshot contable y debe verificarse contra detalles en el momento de consolidación.

## Migraciones y reversión

Cadena separada en esquema y datos, sin editar migraciones aplicadas:

- `pedidos.0009_historialestado_schema`, `0010_historialestado_backfill` (historial + fila inicial por pedido: estado actual, `fecha=actualizado_en`, `actor=NULL`, observación «Estado vigente al migrar (AZ-S1-19); historial previo no disponible»; aborta si falta algún pedido).
- `pagos.0008`–`0018`: elimina check de monto antes de renombrar a `importe` y lo recrea (`pagos_intento_importe_nn`); renombra modelo sin `db_table` explícito; convierte OneToOne→FK y añade campos/índices; backfill/validación de referencias (determinístico para vacías, aborta ante duplicadas no vacías) y endurecimiento de unicidades; guarda de reversión que aborta con `RuntimeError` descriptivo si hay >1 intento por pedido; añade `Venta.intento_aprobado` nullable, lo rellena desde el intento aprobado del mismo pedido (aborta si no existe o no es único) y lo endurece a NOT NULL OneToOne. La reversión restaura datos antes de endurecer columnas y corre la guarda antes del `AlterField` inverso.

Verificada la cadena hacia adelante y la reversión hasta `pedidos.0008`/`pagos.0007` (SQLite y PostgreSQL temporal).

## Acoplamiento y deuda técnica

- `HistorialEstadoPedido` hereda de `inventario.models.ModeloInmutable` (acoplamiento `pedidos→inventario` documentado; verificado sin importación circular con `manage.py check` y suite).
- **Deuda técnica (issue de servicios):** escritura automática del historial en cada transición de estado; idempotencia/concurrencia operativa en procesamiento de pagos; lógica de checkout; validación de servicio de que la venta referencia un intento aprobado del mismo pedido.
- **Efecto funcional:** al pasar de 1:1 a 1:N, un pago rechazado ya no bloquea estructuralmente reintentos del mismo pedido.

## Consecuencias

- Se habilita trazabilidad de intentos e historial de estados a nivel de datos.
- Los importes históricos (`DetallePedido.precio_unitario`/subtotales y `Venta.total`) permanecen como snapshots ante cambios en `OfertaVideojuego.precio_vigente`.
- La coherencia de negocio no garantizable por esquema queda explícitamente documentada y cubierta por pruebas para el estado actual.