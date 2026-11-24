# Diccionario de datos — modelo normalizado

**Issue:** #21 · AZ-S1-19 «Normalizar ciclo transaccional: historial de estados de pedido, intentos de pago y venta aprobada» · **Alcance:** capa de datos.

**Issue:** #22 · AZ-S1-20 «Enriquecer y normalizar los catálogos maestros del videojuego» · **Alcance:** capa de datos y datos de referencia.

Este documento describe el esquema final del backend Django 5.2: tablas,
columnas, reglas de integridad, restricciones SQL e índices. Las restricciones
se implementan en la base de datos (no solo en formularios o servicios) y se
prueban provocando `IntegrityError` sin llamar a `full_clean()`.

Motor de desarrollo/producción: PostgreSQL. Motor de pruebas: SQLite en
memoria (`arkane_zone.settings_test`). Todas las restricciones documentadas se
verifican en ambos motores.

## Convenciones

- **PK:** `BigAutoField` (`bigint` autoincremental) salvo las tablas de Django.
- **FK:** `PROTECT` salvo que se indique otra política. Las referencias
  históricas nunca se borran en cascada.
- **`unique=True`:** índice único de una columna generado por Django.
- **Constraints nombrados explícitamente** para que el error de base de datos
  identifique la regla violada. Los nombres nuevos usan sufijos claros; los
  preexistentes conservan su nombre original.
- **Índices:** nombre explícito de hasta 30 caracteres (límite portable de
  Django).
- **Catálogos de estado (AZ-S1-17):** `codigo` es el identificador estable
  referenciado por las FKs (`to_field="codigo"`); `nombre` es la etiqueta
  visible y editable; `descripcion` es opcional.
- **Catálogo de roles (AZ-S1-18):** `Rol.codigo` es el identificador estable de
  negocio (`cliente`, `administrador`); `Rol.nombre` es la etiqueta visible
  editable. La asignación usuario↔rol se materializa en `cuentas_usuariorol`.

## Resumen de tablas

| App | Tabla | Propósito |
|---|---|---|
| `cuentas` | `cuentas_rol` | Catálogo de roles de negocio. |
| `cuentas` | `cuentas_usuario` | Usuario autenticable (`AbstractUser` + datos de contacto). |
| `cuentas` | `cuentas_usuariorol` | Tabla puente: asignación explícita usuario↔rol. |
| `catalogo` | `catalogo_categoria` | Categoría del título (acción, deportes…). |
| `catalogo` | `catalogo_genero` | Género del título (RPG, shooter…). |
| `catalogo` | `catalogo_plataforma` | Plataforma de la oferta (PC, PS5…). |
| `catalogo` | `catalogo_desarrolladora` | Catálogo maestro de estudios desarrolladores. |
| `catalogo` | `catalogo_distribuidora` | Catálogo maestro de distribuidoras. |
| `catalogo` | `catalogo_clasificacionedad` | Catálogo PEGI de clasificación por edad. |
| `catalogo` | `catalogo_idioma` | Catálogo de idiomas ISO 639-1. |
| `catalogo` | `catalogo_videojuego` | Identidad e información común de un título. |
| `catalogo` | `catalogo_videojuegocategoria` | Tabla puente: categorías de un videojuego. |
| `catalogo` | `catalogo_videojuegogenero` | Tabla puente: géneros de un videojuego. |
| `catalogo` | `catalogo_videojuegodesarrolladora` | Tabla puente: desarrolladoras de un videojuego. |
| `catalogo` | `catalogo_videojuegodistribuidora` | Tabla puente: distribuidoras de un videojuego. |
| `catalogo` | `catalogo_videojuegoidioma` | Tabla puente: idiomas y tipo de presencia. |
| `catalogo` | `catalogo_estadopublicacion` | Catálogo de estados editoriales de una oferta. |
| `catalogo` | `catalogo_ofertavideojuego` | Unidad comercial vendible: videojuego + plataforma. |
| `pedidos` | `pedidos_estadopedido` | Catálogo de estados de un pedido. |
| `pedidos` | `pedidos_pedido` | Pedido (carrito o compra) de un cliente. |
| `pedidos` | `pedidos_detallepedido` | Línea del pedido con precio y snapshots congelados. |
| `pedidos` | `pedidos_historialestadopedido` | Historial inmutable de estados de un pedido. |
| `pagos` | `pagos_estadointentopago` | Catálogo de estados de un intento de pago. |
| `pagos` | `pagos_intentopago` | Intento de pago de un pedido (1:N). |
| `pagos` | `pagos_venta` | Venta consolidada vinculada al intento aprobado. |
| `inventario` | `inventario_tipomovimientoinventario` | Catálogo de tipos de movimiento. |
| `inventario` | `inventario_motivomovimientoinventario` | Catálogo de motivos de movimiento. |
| `inventario` | `inventario_movimientoinventarioofertavideojuego` | Libro mayor inmutable de inventario. |
| `soporte` | `soporte_contacto` | Mensajes del formulario de contacto. |

---

## `cuentas`

### `cuentas_rol`

Catálogo de roles de negocio (AZ-S1-18).

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `codigo` | varchar(50) | no | — | **único**, identificador estable de negocio |
| `nombre` | varchar(50) | no | — | **único**, etiqueta visible editable |
| `descripcion` | text | no | `""` | — |
| `activo` | boolean | no | `true` | — |

Restricción:

| Nombre | Tipo | Regla |
|---|---|---|
| `cuentas_rol_codigo_unico` | `UniqueConstraint` | `codigo` no se repite. |

Roles base sembrados (idempotente): `cliente` (Cliente), `administrador` (Administrador).

### `cuentas_usuario`

Hereda de `AbstractUser`. Se documentan los campos propios y los heredados
relevantes.

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `username` | varchar(150) | no | — | único (Django) |
| `password` | varchar(128) | no | — | hash |
| `email` | varchar(254) | no | `""` | **no único** (deuda técnica) |
| `first_name`, `last_name` | varchar(150) | no | `""` | — |
| `is_staff`, `is_active`, `is_superuser` | boolean | no | según Django | — |
| `last_login`, `date_joined` | timestamp | sí / no | — / auto | — |
| `telefono` | varchar(20) | no | `""` | — |
| `direccion` | text | no | `""` | — |
| `foto` | varchar(100) | sí | `null` | ruta de archivo |

La relación con roles de negocio es **muchos-a-muchos** mediante la tabla puente
`cuentas_usuariorol` (`Usuario.roles`, `through='cuentas.UsuarioRol'`,
`related_name='usuarios'`). No existe la columna `rol_id` (FK directa retirada en
AZ-S1-18).

Relaciones heredadas/técnicas: `groups` (M2M), `user_permissions` (M2M).

### `cuentas_usuariorol`

Tabla puente explícita entre usuario y rol de negocio (AZ-S1-18).

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `usuario_id` | bigint → `cuentas_usuario` | no | — | `CASCADE` (la asignación depende de la cuenta) |
| `rol_id` | bigint → `cuentas_rol` | no | — | `PROTECT` (rol de catálogo no se borra si está asignado) |

Restricciones e índices:

| Nombre | Tipo | Regla / uso |
|---|---|---|
| `cuentas_usuariorol_usuario_rol_unico` | `UniqueConstraint` | La pareja `(usuario, rol)` no se repite. |
| `cuentas_urol_rol_idx` | índice `(rol)` | Búsqueda inversa rol→usuarios. El `UniqueConstraint(usuario, rol)` cubre usuario→roles; no se duplica ese índice. |

Sin metadatos de auditoría (`asignado_en`, `asignado_por`, `activo`). Si en el
futuro se añade `asignado_por` (FK a usuario) hará falta declarar
`through_fields` en el `ManyToManyField`, porque existirían dos FKs a
`cuentas_usuario`.

---

## `catalogo`

### `catalogo_categoria`, `catalogo_genero`, `catalogo_plataforma`

Las tres tablas comparten estructura:

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `nombre` | varchar(100) | no | — | **único** |
| `descripcion` | text | no | `""` | — |
| `activo` | boolean | no | `true` | — |

### `catalogo_videojuego`

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `titulo` | varchar(200) | no | — | — |
| `descripcion` | text | no | `""` | — |
| `portada` | varchar(100) | sí | `null` | ruta de archivo |
| `fecha_lanzamiento` | date | sí | `null` | — |
| `clasificacion_edad` | varchar(20) → `catalogo_clasificacionedad.codigo` | sí | `null` | FK `PROTECT`, `to_field="codigo"`, `db_index=False` (AZ-S1-20) |
| `activo` | boolean | no | `true` | — |
| `creado_en`, `actualizado_en` | timestamp | no | auto | — |

Las columnas `categoria_id` y `genero_id` **ya no existen**: la clasificación
se expresa con las tablas puente `catalogo_videojuegocategoria` y
`catalogo_videojuegogenero`. En el ORM se accede con los M2M
`Videojuego.categorias` y `Videojuego.generos` (con `through` explícito).

Desde AZ-S1-20, `Videojuego` tampoco guarda textos de desarrolladora,
distribuidora ni idioma: se usan los M2M `Videojuego.desarrolladoras`,
`Videojuego.distribuidoras` y `Videojuego.idiomas` con sus tablas puente. La
clasificación por edad es la única FK directa nueva y es nullable. Índice:
`catalogo_vj_clasificacion_idx` sobre `clasificacion_edad` (la FK usa
`db_index=False`).

### `catalogo_videojuegocategoria`

Tabla puente explícita entre un título y una categoría del catálogo.

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `videojuego_id` | bigint → `catalogo_videojuego` | no | — | `CASCADE` (el vínculo no sobrevive al título) |
| `categoria_id` | bigint → `catalogo_categoria` | no | — | `PROTECT` (categoría en uso no se borra) |

Restricciones e índices:

| Nombre | Tipo | Regla |
|---|---|---|
| `catalogo_videojuegocategoria_videojuego_categoria_unicos` | `UniqueConstraint` | La pareja `(videojuego, categoria)` no se repite. |
| `catalogo_vjc_categoria_idx` | índice `(categoria, videojuego)` | Listado de títulos por categoría. |
| `(videojuego, categoria)` | índice único implícito | Cubre el JOIN desde el videojuego hacia sus categorías. |

### `catalogo_videojuegogenero`

Tabla puente explícita entre un título y un género del catálogo.

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `videojuego_id` | bigint → `catalogo_videojuego` | no | — | `CASCADE` (el vínculo no sobrevive al título) |
| `genero_id` | bigint → `catalogo_genero` | no | — | `PROTECT` (género en uso no se borra) |

Restricciones e índices:

| Nombre | Tipo | Regla |
|---|---|---|
| `catalogo_videojuegogenero_videojuego_genero_unicos` | `UniqueConstraint` | La pareja `(videojuego, genero)` no se repite. |
| `catalogo_vjg_genero_idx` | índice `(genero, videojuego)` | Listado de títulos por género. |
| `(videojuego, genero)` | índice único implícito | Cubre el JOIN desde el videojuego hacia sus géneros. |

Un videojuego puede tener **cero, una o varias** categorías y géneros
(`blank=True`); no hay campos adicionales en las tablas puente porque la pareja
no tiene atributos propios de dominio.

### Catálogos maestros: `catalogo_desarrolladora`, `catalogo_distribuidora`, `catalogo_clasificacionedad`, `catalogo_idioma`

Catálogos de referencia de AZ-S1-20; `id` es bigint PK. `codigo` es el
identificador estable (slug, ISO 639-1 o código PEGI) y `nombre` la etiqueta
visible.

| Tabla | Campos propios | Restricciones |
|---|---|---|
| `catalogo_desarrolladora` | `codigo` varchar(100), `nombre` varchar(150), `activo` bool | `catalogo_desarrolladora_codigo_unico`; `catalogo_desarrolladora_nombre_unico` (`Lower("nombre")`) |
| `catalogo_distribuidora` | `codigo` varchar(100), `nombre` varchar(150), `activo` bool | `catalogo_distribuidora_codigo_unico`; `catalogo_distribuidora_nombre_unico` (`Lower("nombre")`) |
| `catalogo_clasificacionedad` | `codigo` varchar(20), `nombre` varchar(50), `orden` smallint | `catalogo_clasificacionedad_codigo_unico`; `catalogo_clasificacionedad_nombre_unico` |
| `catalogo_idioma` | `codigo` varchar(2), `nombre` varchar(100) | `catalogo_idioma_codigo_unico`; `catalogo_idioma_nombre_unico` (`Lower("nombre")`) |

Se siembran de forma idempotente las clasificaciones PEGI `3`, `7`, `12`, `16`,
`18` y los idiomas `es`, `en`, `fr`, `de`, `it`, `pt`, `ja`, `ko`, `zh`, `ru`;
no se siembran desarrolladoras ni distribuidoras.

### Tablas puente: `catalogo_videojuegodesarrolladora`, `catalogo_videojuegodistribuidora`, `catalogo_videojuegoidioma`

Asocian un título con un catálogo; `id` es bigint PK, el lado `videojuego` es
`CASCADE` y el lado catálogo `PROTECT`.

| Tabla | Columnas | Restricciones e índices |
|---|---|---|
| `catalogo_videojuegodesarrolladora` | `videojuego_id`, `desarrolladora_id` | `catalogo_vjdesarrolladora_unicos` (`(videojuego, desarrolladora)`); índice `catalogo_vjd_desarroll_idx` (`(desarrolladora, videojuego)`) |
| `catalogo_videojuegodistribuidora` | `videojuego_id`, `distribuidora_id` | `catalogo_vjdistribuidora_unicos` (`(videojuego, distribuidora)`); índice `catalogo_vjd_distrib_idx` (`(distribuidora, videojuego)`) |
| `catalogo_videojuegoidioma` | `videojuego_id`, `idioma_id`, `tipo` varchar(10) | `catalogo_vjidioma_tipo_unicos` (`(videojuego, idioma, tipo)`); `catalogo_vji_tipo_valido` (`tipo` ∈ `audio`/`interfaz`/`subtitulos`); índice `catalogo_vji_idioma_tipo_idx` (`(idioma, tipo, videojuego)`) |

Un título puede tener cero, una o varias filas en cada puente (`blank=True`); un
mismo idioma se repite si cambia el `tipo` (audio, interfaz, subtítulos).

### `catalogo_estadopublicacion`

Catálogo relacional de estados editoriales (AZ-S1-17).

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `codigo` | varchar(50) | no | — | **único**, identificador estable |
| `nombre` | varchar(100) | no | — | etiqueta visible editable |
| `descripcion` | text | no | `""` | — |

Constraint: `catalogo_estadopublicacion_codigo_unico` (`codigo` único).

Valores sembrados: `borrador` (Borrador), `publicado` (Publicado),
`retirado` (Retirado).

### `catalogo_ofertavideojuego`

Unidad comercial vendible. Concentra precio, SKU, stock y publicación.

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `videojuego_id` | bigint → `catalogo_videojuego` | no | — | `PROTECT` |
| `plataforma_id` | bigint → `catalogo_plataforma` | no | — | `PROTECT` |
| `precio_vigente` | numeric(10,2) | no | — | `>= 0` |
| `sku` | varchar(50) | no | — | **único** |
| `stock` | integer | no | `0` | `>= 0` (implícito de `PositiveIntegerField`) |
| `estado_publicacion` | varchar(50) → `catalogo_estadopublicacion.codigo` | no | `publicado` | FK `PROTECT`, `to_field="codigo"`, `db_index=False` |
| `creado_en`, `actualizado_en` | timestamp | no | auto | — |

Restricciones:

| Constraint | Regla |
|---|---|
| `catalogo_ofertavideojuego_videojuego_plataforma_unicos` | `(videojuego, plataforma)` único. |
| `catalogo_ofertavideojuego_precio_vigente_no_negativo` | `precio_vigente >= 0`. |
| `sku` (`unique=True`) | SKU interno único. |
| FK `estado_publicacion` | Solo códigos existentes en `catalogo_estadopublicacion`. |

Índices:

| Índice | Columnas | Uso |
|---|---|---|
| `catalogo_oferta_est_stock_idx` | `(estado_publicacion, stock)` | Storefront: publicadas con stock. |
| `catalogo_oferta_plat_est_idx` | `(plataforma, estado_publicacion)` | Catálogo por plataforma. |

---

## `pedidos`

### `pedidos_estadopedido`

Catálogo relacional de estados de pedido (AZ-S1-17).

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `codigo` | varchar(50) | no | — | **único**, identificador estable |
| `nombre` | varchar(100) | no | — | etiqueta visible editable |
| `descripcion` | text | no | `""` | — |

Constraint: `pedidos_estadopedido_codigo_unico` (`codigo` único).

Valores sembrados: `pendiente` (Pendiente), `pagado` (Pagado),
`cancelado` (Cancelado).

### `pedidos_pedido`

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `cliente_id` | bigint → `cuentas_usuario` | no | — | `PROTECT` |
| `estado` | varchar(50) → `pedidos_estadopedido.codigo` | no | `pendiente` | FK `PROTECT`, `to_field="codigo"`, `db_index=False` |
| `creado_en` | timestamp | no | auto | — |
| `actualizado_en` | timestamp | no | auto | — |

Índice:

| Índice | Columnas | Uso |
|---|---|---|
| `pedidos_pedido_cli_fecha_idx` | `(cliente, -creado_en)` | Historial de compras del cliente, más reciente primero. |

> **Deuda técnica:** no existe una restricción que garantice un único pedido
> `pendiente` por cliente. `get_or_create_carrito()` mitiga el caso normal,
> pero dos peticiones concurrentes podrían crear dos carritos.

### `pedidos_detallepedido`

Línea histórica del pedido. Congela precio unitario y snapshots de título y
plataforma; no cambia si el catálogo se modifica después.

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `pedido_id` | bigint → `pedidos_pedido` | no | — | `CASCADE` (el pedido es dueño de sus líneas) |
| `oferta_id` | bigint → `catalogo_ofertavideojuego` | no | — | `PROTECT` |
| `cantidad` | integer | no | `1` | `>= 1` |
| `precio_unitario` | numeric(10,2) | no | — | `>= 0` |
| `titulo_snapshot` | varchar(200) | no | — | congelado al crear |
| `plataforma_snapshot` | varchar(100) | no | — | congelado al crear |

Restricciones:

| Constraint | Regla |
|---|---|
| `pedidos_detallepedido_pedido_oferta_unicos` | `(pedido, oferta)` único: una sola línea por oferta en el pedido. |
| `pedidos_detallepedido_cantidad_positiva` | `cantidad >= 1`: no existen líneas de cantidad cero o negativa. |
| `pedidos_detallepedido_precio_unitario_no_negativo` | `precio_unitario >= 0`. |

### `pedidos_historialestadopedido`

Historial inmutable (solo-apéndice) de estados de un pedido (AZ-S1-19). Hereda el
comportamiento de inmutabilidad de `inventario.models.ModeloInmutable` (acoplamiento
documentado `pedidos→inventario`).

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `pedido_id` | bigint → `pedidos_pedido` | no | — | `PROTECT` |
| `estado` | varchar(50) → `pedidos_estadopedido.codigo` | no | — | FK `PROTECT`, `to_field="codigo"`, `db_index=False` |
| `fecha` | timestamp | no | `now` | momento del registro (editable=False) |
| `actor_id` | bigint → `cuentas_usuario` | sí | `null` | `PROTECT`; NULL si sistema/migración |
| `observacion` | text | no | `""` | — |

Índice:

| Índice | Columnas | Uso |
|---|---|---|
| `pedidos_hist_ped_fec_idx` | `(pedido, fecha)` | Historial cronológico del pedido. |

> La escritura automática del historial en cada transición de estado es
> responsabilidad del servicio (deuda técnica, issue de servicios). La migración
> inserta una fila inicial por pedido existente con `estado` actual,
> `fecha=actualizado_en`, `actor=NULL` y observación
> «Estado vigente al migrar (AZ-S1-19); historial previo no disponible».

---

## `pagos`

### `pagos_estadointentopago`

Catálogo relacional de estados de intento de pago (AZ-S1-17).

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `codigo` | varchar(50) | no | — | **único**, identificador estable |
| `nombre` | varchar(100) | no | — | etiqueta visible editable |
| `descripcion` | text | no | `""` | — |

Constraint: `pagos_estadointentopago_codigo_unico` (`codigo` único).

Valores sembrados: `aprobado` (Aprobado), `rechazado` (Rechazado),
`pendiente` (Pendiente).

### `pagos_intentopago`

Intento de pago asociado a un pedido (AZ-S1-19; antes `pagos_pago`). Relación 1:N
con `Pedido`: un pedido puede tener varios intentos (p. ej. tras rechazo). No se
almacenan datos de tarjetas ni credenciales financieras.

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `pedido_id` | bigint → `pedidos_pedido` | no | — | FK `PROTECT` (`related_name=intentos_pago`) |
| `importe` | numeric(10,2) | no | — | `>= 0` (snapshot monetario del intento) |
| `estado` | varchar(50) → `pagos_estadointentopago.codigo` | no | `pendiente` | FK `PROTECT`, `to_field="codigo"`, `db_index=False` |
| `referencia` | varchar(100) | no | — | **única** (identidad interna trazable) |
| `clave_idempotencia` | varchar(200) | no | `""` | **única cuando no está vacía** |
| `creado_en` | timestamp | no | auto | — |
| `actualizado_en` | timestamp | no | auto | — |

Restricciones e índices:

| Nombre | Tipo | Regla / uso |
|---|---|---|
| `pagos_intento_importe_nn` | check | `importe >= 0`. |
| `pagos_intento_ref_unico` | unique | `referencia` no se repite. |
| `pagos_intento_idem_unico` | unique condicional | `clave_idempotencia` única si `<> ''`. |
| `pagos_intento_ped_fec_idx` | index `(pedido, -creado_en)` | Historial de intentos por pedido. |
| `pagos_intento_est_fec_idx` | index `(estado, -creado_en)` | Consultas por estado y fecha. |

> Propiedad de compatibilidad de solo lectura: `Pedido.pago` devuelve el intento
> aprobado del pedido (o `None`).

### `pagos_venta`

Venta consolidada de un pedido completado (AZ-S1-19).

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `pedido_id` | bigint → `pedidos_pedido` | no | — | `PROTECT`, **único** (`OneToOne`) |
| `intento_aprobado_id` | bigint → `pagos_intentopago` | no | — | `PROTECT`, **único** (`OneToOne`): intento que originó la venta |
| `total` | numeric(10,2) | no | — | `>= 0`, **snapshot contable** (verificable contra suma de detalles al momento de la venta) |
| `registrada_en` | timestamp | no | auto | — |

Restricciones e índices:

| Nombre | Tipo | Regla / uso |
|---|---|---|
| `pagos_venta_pedido_id_key` | unique (OneToOne) | Una venta por pedido. |
| `pagos_venta_intento_aprobado_id_key` | unique (OneToOne) | Un intento origina como máximo una venta. |
| `pagos_venta_total_no_negativo` | check | `total >= 0`. |
| `pagos_venta_registrada_idx` | index `(registrada_en)` | Reportes de ventas por fecha. |

---

## `inventario`

### `inventario_tipomovimientoinventario`

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `codigo` | varchar(50) | no | — | **único** |
| `nombre` | varchar(100) | no | — | — |
| `descripcion` | text | no | `""` | — |
| `naturaleza` | varchar(10) | no | — | `entrada`/`salida`/`ajuste` (`TextChoices`, sin `CheckConstraint`; decisión de alcance AZ-S1-17) |
| `activo` | boolean | no | `true` | — |

Constraint: `inventario_tipomovimiento_codigo_unico` (`codigo` único).

### `inventario_motivomovimientoinventario`

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `codigo` | varchar(50) | no | — | **único** |
| `nombre` | varchar(100) | no | — | — |
| `descripcion` | text | no | `""` | — |
| `activo` | boolean | no | `true` | — |

Constraint: `inventario_motivomovimiento_codigo_unico` (`codigo` único).

### `inventario_movimientoinventarioofertavideojuego`

Libro mayor inmutable (solo-apéndice) con saldos corridos congelados. Ver
`docs/adr_az-s1-14-libro-mayor-inventario.md`.

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `oferta_id` | bigint → `catalogo_ofertavideojuego` | no | — | `PROTECT` |
| `tipo_movimiento_id` | bigint → `inventario_tipomovimientoinventario` | no | — | `PROTECT` |
| `motivo_id` | bigint → `inventario_motivomovimientoinventario` | sí | `null` | `PROTECT` |
| `observacion` | text | no | `""` | — |
| `cantidad` | integer | no | — | `> 0` |
| `unidad` | varchar(50) | no | `unidad` | — |
| `saldo_anterior` | integer | no | — | `>= 0` |
| `saldo_posterior` | integer | no | — | `>= 0` |
| `fecha_hora` | timestamp | no | `now` | no editable |
| `usuario_responsable_id` | bigint → `cuentas_usuario` | sí | `null` | `PROTECT` |
| `detalle_pedido_id` | bigint → `pedidos_detallepedido` | sí | `null` | `PROTECT`, único condicional |
| `clave_idempotencia` | varchar(200) | no | — | **único** |
| `movimiento_compensado_id` | bigint → self | sí | `null` | `PROTECT` |

Restricciones:

| Constraint | Regla |
|---|---|
| `inventario_movimiento_clave_idempotencia_unica` | `clave_idempotencia` única. |
| `inventario_movimiento_detalle_pedido_unico` | `detalle_pedido` único solo cuando no es `null`. |
| `inventario_movimiento_cantidad_positiva` | `cantidad > 0`. |
| `inventario_movimiento_saldo_anterior_no_negativo` | `saldo_anterior >= 0`. |
| `inventario_movimiento_saldo_posterior_no_negativo` | `saldo_posterior >= 0`. |

Índices:

| Índice | Columnas | Uso |
|---|---|---|
| `inventario_oferta_fecha_idx` | `(oferta, -fecha_hora)` | Historial de una oferta. |
| `inventario_mov_tipo_fecha_idx` | `(tipo_movimiento, -fecha_hora)` | Movimientos recientes por tipo. |

> **Riesgo de consistencia:** `catalogo_ofertavideojuego.stock` es un contador
> y el ledger es la fuente auditable. Hoy `pagos.services` descuenta `stock`
> sin escribir un movimiento. Mientras el servicio no escriba ambos en la
> misma transacción, el stock puede divergir del último `saldo_posterior`.

---

## `soporte`

### `soporte_contacto`

| Campo | Tipo | Nulo | Default | Regla |
|---|---|---|---|---|
| `id` | bigint | no | auto | PK |
| `nombre` | varchar(150) | no | — | — |
| `email` | varchar(254) | no | — | — |
| `telefono` | varchar(20) | no | `""` | — |
| `asunto` | varchar(200) | no | — | — |
| `mensaje` | text | no | `""` | — |
| `usuario_id` | bigint → `cuentas_usuario` | sí | `null` | `SET_NULL` |
| `creado_en` | timestamp | no | auto | — |
| `atendido` | boolean | no | `false` | — |

---

## Estados y decisiones de alcance (AZ-S1-17)

Los estados de `Pedido`, `IntentoPago` (intento de pago) y `OfertaVideojuego` se
normalizaron como catálogos relacionales con FKs por `to_field="codigo"` y
`PROTECT`. Las etiquetas (`nombre`) son editables sin alterar los datos
transaccionales; los códigos son estables. No se implementa lógica de transición
(ver `docs/adr_az-s1-17-estados-catalogo.md`).

**Excepción documentada:** `inventario_tipomovimientoinventario.naturaleza`
permanece como `TextChoices` (`entrada`/`salida`/`ajuste`) sin
`CheckConstraint`. Es un dominio cerrado que determina la aritmética del ledger
(AZ-S1-14); no se convierte ni se duplica.

Consecuencia actual de `naturaleza`: un `UPDATE` directo por SQL puede escribir
un valor fuera del dominio. La validación de `choices` solo ocurre en
formularios y en `full_clean()`, que el ORM no invoca automáticamente.

## Roles de negocio y decisiones de alcance (AZ-S1-18)

`Rol` es un catálogo de negocio con `codigo` estable y `nombre` editable. La
asignación usuario↔rol es muchos-a-muchos explícita mediante `cuentas_usuariorol`
(`UniqueConstraint(usuario, rol)`, `on_delete` `usuario=CASCADE`, `rol=PROTECT`,
índice `cuentas_urol_rol_idx` para rol→usuarios). No hay metadatos de
auditoría; si se añade `asignado_por` en el futuro hará falta `through_fields`.

`is_superuser`, `is_staff`, `Group` y `Permission` de Django no se replican ni se
sincronizan con `Rol`; ver `docs/adr_az-s1-18-roles-usuario.md`.

## Catálogos maestros y decisiones de alcance (AZ-S1-20)

`Desarrolladora`, `Distribuidora`, `ClasificacionEdad` e `Idioma` son catálogos
maestros: `codigo` es el identificador estable y `nombre` la etiqueta visible
(único sin mayúsculas con `Lower("nombre")`, salvo clasificación, único exacto).
Antes de cargar o sembrar se recortan extremos y se colapsan espacios con
`catalogo.models.normalizar_nombre_catalogo`; la base de datos cubre mayúsculas,
no espacios.

Desarrolladora y distribuidora son M:N con tablas puente y
`UniqueConstraint(videojuego, entidad)`; idioma usa una puente con `tipo`,
`CheckConstraint` y `UniqueConstraint(videojuego, idioma, tipo)`.
`Videojuego.clasificacion_edad` es FK nullable por `to_field="codigo"` y
`PROTECT`. El lado catálogo es `PROTECT`; el lado videojuego de las puentes es
`CASCADE`.

No se crea `Caracteristica` ni campos técnicos (sin conjunto de datos acordado)
ni una edad numérica libre (la clasificación es el catálogo PEGI). El esquema
anterior nunca tuvo columnas de texto de estos atributos, así que no hubo
backfill legado. Ver `docs/adr_az-s1-20-catalogos-maestros.md`.

## Migraciones que materializan este esquema

| Migración | Contenido |
|---|---|
| `catalogo.0003_indices_catalogo` | Reemplaza `catalogo_oferta_estado_idx` por `catalogo_oferta_est_stock_idx`; agrega índices compuestos de catálogo. |
| `catalogo.0004_tablas_puente_categoria_genero` | Crea tablas puente M2M. Solo esquema. |
| `catalogo.0005_videojuego_categoria_genero_opcionales` | Relaja FKs directas a `NULL`. Solo esquema. |
| `catalogo.0006_copiar_asociaciones_catalogo` | Copia asociaciones a las tablas puente (idempotente). Solo datos. |
| `catalogo.0007_retirar_fks_categoria_genero` | Retira FKs directas y añade M2M. Solo esquema. |
| `pedidos.0003_integridad_detallepedido` | Índice de cliente/fecha; valida datos y agrega checks de `cantidad` y `precio_unitario`. |
| `pagos.0002_integridad_pagos` | Índice de ventas por fecha; valida datos y agrega checks de `monto` y `total`. |
| `pedidos.0004_estado_pedido` | Crea `pedidos_estadopedido`. Solo esquema. |
| `pedidos.0005_semilla_estados_pedido` | Siembra estados de pedido (idempotente). Solo datos. |
| `pedidos.0006_pedido_estado_fk` | Renombra `estado` a `estado_legacy`, lo relaja y agrega FK nullable. Solo esquema. |
| `pedidos.0007_copiar_estado_pedido` | Copia/valida estados de pedido a la FK; aborta con tabla/campo/valor/cantidad si hay desconocidos. Solo datos. |
| `pedidos.0008_pedido_estado_definitivo` | Elimina `estado_legacy` y deja la FK `NOT NULL` con default. Solo esquema. |
| `pagos.0003_estado_intento_pago` | Crea `pagos_estadointentopago`. Solo esquema. |
| `pagos.0004_semilla_estados_pago` | Siembra estados de intento de pago. Solo datos. |
| `pagos.0005_pago_estado_fk` | Prepara la FK de estado en pago. Solo esquema. |
| `pagos.0006_copiar_estado_pago` | Copia/valida estados de pago a la FK. Solo datos. |
| `pagos.0007_pago_estado_definitivo` | Consolida la FK de estado en pago. Solo esquema. |
| `catalogo.0008_estado_publicacion` | Crea `catalogo_estadopublicacion`. Solo esquema. |
| `catalogo.0009_semilla_estados_publicacion` | Siembra estados de publicación. Solo datos. |
| `catalogo.0010_oferta_estado_fk` | Retira índices de oferta, prepara la FK de publicación. Solo esquema. |
| `catalogo.0011_copiar_estado_publicacion` | Copia/valida estados de publicación a la FK. Solo datos. |
| `catalogo.0012_oferta_estado_definitivo` | Consolida la FK de publicación y recrea índices. Solo esquema. |
| `cuentas.0002_rol_codigo_nullable` | Añade `codigo` a `cuentas_rol` nullable, sin unique. Solo esquema. |
| `cuentas.0003_poblar_codigo_roles` | Puebla `codigo` con mapeo explícito desde `nombre`, garantiza roles base (idempotente); aborta con tabla/campo/valor/cantidad ante nombres sin mapeo o colisiones. Solo datos. |
| `cuentas.0004_rol_codigo_definitivo` | `codigo` NOT NULL + `cuentas_rol_codigo_unico`. Solo esquema. |
| `cuentas.0005_usuariorol_puente` | Crea `cuentas_usuariorol` con `cuentas_usuariorol_usuario_rol_unico` y `cuentas_urol_rol_idx`. Solo esquema. |
| `cuentas.0006_copiar_roles_usuario` | Copia `Usuario.rol` no nulo a asignaciones iniciales (idempotente); usuarios sin rol quedan sin asignación. Reverso restaura según prioridad documentada. Solo datos. |
| `cuentas.0007_usuario_roles_m2m` | Retira `Usuario.rol` y añade M2M `roles` (`through=UsuarioRol`). Solo esquema. |
| `pedidos.0009_historialestado_schema` | Crea `pedidos_historialestadopedido` e índice `pedidos_hist_ped_fec_idx`. Solo esquema. |
| `pedidos.0010_historialestado_backfill` | Inserta historial inicial por pedido existente (`estado` actual, `fecha=actualizado_en`, `actor=NULL`, observación de migración); aborta si algún pedido queda sin fila. Reverso elimina esas filas. Solo datos. |
| `pagos.0008_remove_check_monto` | Elimina `pagos_pago_monto_no_negativo` antes del renombre de campo. Solo esquema. |
| `pagos.0009_rename_monto_importe` | Renombra `monto` → `importe`. Solo esquema. |
| `pagos.0010_check_importe` | Agrega `pagos_intento_importe_nn` sobre `importe`. Solo esquema. |
| `pagos.0011_rename_model_intento` | Renombra `Pago` → `IntentoPago` (tabla pasa a `pagos_intentopago`). Solo esquema. |
| `pagos.0012_intentopago_schema_campos` | Convierte `pedido` a FK (1:N), ajusta `estado`, añade `clave_idempotencia`/`actualizado_en` e índices `pagos_intento_ped_fec_idx`, `pagos_intento_est_fec_idx`. Solo esquema. |
| `pagos.0013_intentopago_datos_backfill` | Rellena referencias vacías (`LEGACY-<pk>`) y `actualizado_en`; aborta ante referencias no vacías duplicadas (tabla, campo, valor, cantidad). Reverso restaura referencias generadas. Solo datos. |
| `pagos.0014_intentopago_constraints` | Endurece `referencia`/`actualizado_en` y añade `pagos_intento_ref_unico`, `pagos_intento_idem_unico`. Solo esquema. |
| `pagos.0015_guardia_reversion_onetoone` | Guardia de reversión: al revertir verifica ≤1 intento por pedido y aborta con `RuntimeError` descriptivo si no (tabla, campo, cantidad). Solo datos. |
| `pagos.0016_venta_intento_nullable` | Añade `Venta.intento_aprobado` nullable (FK). Solo esquema. |
| `pagos.0017_venta_intento_backfill` | Vincula cada venta con el intento aprobado del mismo pedido; aborta si no existe o no es único (tabla, campo, cantidad/pedido). Reverso limpia el vínculo. Solo datos. |
| `pagos.0018_venta_intento_definitivo` | Endurece `intento_aprobado` a NOT NULL `OneToOne` (`PROTECT`). Solo esquema. |
| `catalogo.0013_catalogos_maestros` | Crea `Desarrolladora`, `Distribuidora`, `ClasificacionEdad`, `Idioma`, las tres puentes, los M2M de `Videojuego`, la FK nullable `clasificacion_edad` y sus índices. Solo esquema. |
| `catalogo.0014_semilla_catalogos_maestros` | Siembra idempotente de clasificaciones PEGI e idiomas comunes; el reverso aborta con mensaje claro si hay datos nuevos y elimina solo lo sembrado. Solo datos. |

Las migraciones de datos no normalizan nada: si encuentran filas inválidas
abortan con un `RuntimeError` que indica tabla, campo y cantidad de filas
afectadas. El operador debe corregir los datos y reintentar. La validación se
ejecuta antes de agregar los `CheckConstraint`, de modo que nunca se aplica un
check sobre datos que lo violan.

`catalogo.0006_copiar_asociaciones_catalogo` es reversible con una limitación
documentada: la reversión restaura la asociación de **menor PK** y descarta las
adicionales. Si algún videojuego no tiene categoría o género, aborta con un
`RuntimeError` descriptivo.

Las migraciones de estados (AZ-S1-17) son reversibles con datos: la restauración
del valor al campo antiguo ocurre antes de volver a `NOT NULL`. Si hay códigos
nuevos usados que no existen en el esquema anterior, la reversión aborta con un
mensaje claro. El reverso de la siembra falla si hay filas que referencian los
catálogos (`PROTECT`).

Las migraciones de roles (AZ-S1-18) son reversibles hasta `cuentas.0001_initial`
con datos: al revertir, si un usuario tiene varios roles se restaura
`administrador` si existe; si no, la asignación de menor PK; las asignaciones
adicionales se pierden (la FK monovaluada no puede representarlas). `0003` aborta
con mensaje claro ante nombres sin mapeo o colisiones de código.

Las migraciones del ciclo transaccional (AZ-S1-19) son reversibles con datos hasta
`pedidos.0008`/`pagos.0007`: se restaura `Pago` (OneToOne, `monto`) y se elimina
`intento_aprobado`/historial en el orden correcto. La reversión aborta con
`RuntimeError` descriptivo si algún pedido tiene más de un intento (guardia
`pagos.0015` antes del `AlterField` inverso) o si hay datos incompatibles con el
esquema anterior.

## Deudas técnicas y brechas conocidas

1. **`Usuario.email` no es único** (`cuentas`, fuera de alcance). Un mismo
   correo puede asociarse a varias cuentas.
2. **Idempotencia operativa de pagos en servicios.** La BD garantiza unicidad de
   `referencia` y unicidad condicional de `clave_idempotencia`, pero el servicio
   de checkout/procesamiento debe aplicar idempotencia y concurrencia (deuda
   técnica, issue de servicios).
3. **Escritura automática del historial.** `HistorialEstadoPedido` conserva
   transiciones registradas; la escritura automática en cada transición queda en
   servicios (deuda técnica). Un pago rechazado ya no bloquea reintentos
   (intentos 1:N).
4. **Múltiples pedidos `pendiente` por cliente.** No hay restricción parcial
   que garantice un único carrito activo.
5. **Stock vs. libro mayor.** `pagos.services` modifica `stock` sin registrar
   un movimiento de inventario.
6. **`naturaleza` sin `CheckConstraint`.** `TipoMovimientoInventario.naturaleza`
   sigue siendo `TextChoices` (decisión AZ-S1-17).
7. **Sin validación de transiciones.** Los catálogos de estado garantizan
   integridad referencial, no flujos de transición (ver ADR AZ-S1-17).
8. **`flush` y catálogos.** Tras un `flush`, los catálogos de estado y los roles
   base quedan vacíos; `seed_catalogo` los repone de forma idempotente y en
   pruebas se garantizan mediante fixtures autouse idempotentes.
9. **Compatibilidad transitoria `is_staff` ↔ rol de negocio.** `es_administrador`
   conserva `True` para usuarios `is_staff` sin exigir asignación del rol
   `administrador` (para no cambiar autorización). La frontera técnica/negocio
   se documenta en `docs/adr_az-s1-18-roles-usuario.md`.
10. **Coherencia venta↔intento no garantizable solo en BD.** La BD no garantiza que
    `Venta.intento_aprobado` pertenezca al mismo `pedido` de la venta ni que el
    intento esté en estado aprobado (se cubre en pruebas y queda para el issue de
    servicios/checkout). `DetallePedido.pedido` sigue con `CASCADE` (documentado).
