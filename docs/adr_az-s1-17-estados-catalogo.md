# ADR AZ-S1-17 — Estados de dominio normalizados mediante catálogos

**Estado:** aceptado  
**Fecha:** 2026-11-15  
**Issue:** #19 · AZ-S1-17 «Eliminar enumerados de dominio y normalizar estados mediante tablas catálogo»

## Contexto

Los estados de negocio persistentes estaban modelados como `TextChoices`/`choices`
en los campos `pedidos.Pedido.estado`, `pagos.Pago.estado` y
`catalogo.OfertaVideojuego.estado_publicacion`. Esto permitía valores fuera del
dominio mediante SQL directo (sin `CheckConstraint` en base de datos) y hacía
que agregar o renombrar una etiqueta implicara cambios de código y esquema.

AZ-S1-14 ya introdujo catálogos relacionales para inventario
(`TipoMovimientoInventario`, `MotivoMovimientoInventario`); este trabajo extiende
ese patrón a los estados transaccionales.

## Decisión

### 1. Qué se convierte y qué no

| Campo | Decisión |
|---|---|
| `pedidos.Pedido.estado` | Convertido a FK `pedidos.EstadoPedido`. |
| `pagos.Pago.estado` | Convertido a FK `pagos.EstadoIntentoPago`. |
| `catalogo.OfertaVideojuego.estado_publicacion` | Convertido a FK `catalogo.EstadoPublicacion`. |
| `inventario.TipoMovimientoInventario.naturaleza` | **No se convierte.** Es un atributo cerrado del catálogo que define la aritmética del ledger (`entrada`/`salida`/`ajuste`), no un estado transaccional; cambiarlo exigiría lógica de negocio y no aporta el mismo beneficio. Se documenta como decisión de alcance (AZ-S1-14). |

No se duplica ni se recrea `TipoMovimientoInventario`.

### 2. Modelo de catálogo

Cada catálogo define: `codigo` (`CharField(max_length=50)`, único, identificador
estable), `nombre` (`CharField(max_length=100)`, etiqueta visible editable) y
`descripcion` (`TextField(blank=True)`). No se incluye `activo`: los estados son
un protocolo cerrado y no hay selección de estados por parte del usuario; incluir
`activo` sin filtrar sería un campo muerto y filtrarlo impediría editar filas
históricas.

`on_delete=PROTECT`, `related_name` `pedidos`/`pagos`/`ofertas`.

### 3. FK por `to_field="codigo"` (opción B)

Las FKs usan `to_field="codigo"`, `db_column` con el nombre original del campo
(`estado` / `estado_publicacion`) y `db_index=False`. El valor persistido sigue
siendo el código estable (`"pendiente"`, `"pagado"`, etc.), por lo que
`.values("estado")`, filtros por código y el dashboard de reportes siguen
funcionando sin cambios estructurales. `estado_id` en el ORM contiene el código
(string), no un entero; las asignaciones se hacen con `estado_id` o con la
instancia del catálogo. Django 5.2 acepta `UniqueConstraint(codigo)` como destino
de `to_field`.

Se conservan los defaults por código (`"pendiente"` / `"publicado"`). En
`catalogo_ofertavideojuego` se eliminan y recrean los índices compuestos
`catalogo_oferta_est_stock_idx` y `catalogo_oferta_plat_est_idx` con sus nombres
originales.

### 4. Códigos sembrados

| Catálogo | Códigos → etiquetas |
|---|---|
| `pedidos.EstadoPedido` | `pendiente`→Pendiente, `pagado`→Pagado, `cancelado`→Cancelado |
| `pagos.EstadoIntentoPago` | `aprobado`→Aprobado, `rechazado`→Rechazado, `pendiente`→Pendiente |
| `catalogo.EstadoPublicacion` | `borrador`→Borrador, `publicado`→Publicado, `retirado`→Retirado |

La siembra es idempotente (`get_or_create` por código) y no sobrescribe etiquetas
editadas.

### 5. Migraciones

Cinco pasos por app, separados en esquema y datos (15 migraciones nuevas), sin
editar migraciones aplicadas:

1. Esquema: crear catálogo.
2. Datos: sembrar códigos (`get_or_create`).
3. Esquema: renombrar el campo viejo a `*_legacy`, relajarlo a `NULL`, agregar FK
   nullable con `db_column` original.
4. Datos: validar que cada valor existente esté en el catálogo y copiar; abortar
   con `RuntimeError` indicando tabla, campo, valor desconocido y cantidad de
   filas si hay valores fuera del dominio o `NULL`. La reversión copia la FK a
   `*_legacy` y aborta si encuentra códigos nuevos sin equivalente histórico.
5. Esquema: eliminar `*_legacy`, dejar la FK `NOT NULL` con default y recrear
   índices en catálogo.

La reversión restaura datos **antes** de volver a `NOT NULL`. El reverso de la
siembra borra por código y, ante `ProtectedError`, aborta con un mensaje claro
que indica el código y las tablas que referencian el catálogo.

### 6. Transiciones de estado (documentación, sin lógica)

La base de datos garantiza la integridad referencial (FK + `PROTECT`), **no** las
transiciones. No se implementan workflows ni validaciones de transición.

#### Pedido

| Desde | Hacia | Disparador previsto | ¿Implementado hoy? |
|---|---|---|---|
| `pendiente` | `pagado` | Pago aprobado. | Sí. |
| `pendiente` | `cancelado` | Cancelación del cliente. | Sí. |
| Cualquier otra | Cualquier otra | — | No. |

#### Intento de pago

| Desde | Hacia | Disparador previsto | ¿Implementado hoy? |
|---|---|---|---|
| `pendiente` | `aprobado` | Pasarela aprueba. | No: se crea directamente `aprobado`. |
| `pendiente` | `rechazado` | Pasarela rechaza. | No: se crea directamente `rechazado`. |
| Cualquier otra | Cualquier otra | Reintento, etc. | No. |

> Deuda existente: `Pago.pedido` es `OneToOne`; un pago rechazado bloquea un
> reintento estructuralmente.

#### Publicación de oferta

| Desde | Hacia | Disparador previsto | ¿Implementado hoy? |
|---|---|---|---|
| `borrador` | `publicado` | Publicación editorial. | No: el admin permite cualquier cambio. |
| `publicado` | `retirado` | Retiro. | No. |
| `retirado` | `publicado` | Republicación. | No. |
| Cualquier otra | Cualquier otra | — | No. |

## Alcance aplicado

- **Modificados (autorizados):** `models`, migraciones, `tests`, `docs/`, y los
  cambios mínimos en `pedidos/services.py`, `pagos/services.py`, `pagos/views.py`,
  `reportes/views.py`, los templates `pedidos/mis_pedidos.html`,
  `pedidos/detalle.html`, `reportes/reporte_inventario.html` y
  `catalogo/management/commands/seed_catalogo.py` (siembra idempotente de
  catálogos para tolerar `flush`).
- **No modificado:** admin, `catalogo/views.py` (usa `publicadas()` del modelo),
  `pedidos/views.py`, frontend, ni lógica de transición. No se registraron los
  catálogos en el admin ni se añadieron `select_related`.
- **Sin `get_estado_display`:** se usa `estado_id` para comparar y `estado.nombre`
  para mostrar.

## Deuda técnica que queda

- `inventario.TipoMovimientoInventario.naturaleza` sigue como `TextChoices` sin
  `CheckConstraint` (decisión de alcance).
- No hay validación de transiciones entre estados.
- `Pago.referencia` sin unicidad/obligatoriedad y `Pago.pedido` `OneToOne`
  impiden modelar reintentos.
- Un `flush` borra los catálogos; `seed_catalogo` los repone, pero cualquier otro
  flujo que dependa del default sin sembrar debe hacerlo explícitamente.
- No hay `select_related("estado")` añadido en vistas; las plantillas que acceden a
  `estado.nombre` pueden generar consultas adicionales en listados.
- El usuario ejecuta `git add`, `commit` y `push`.
