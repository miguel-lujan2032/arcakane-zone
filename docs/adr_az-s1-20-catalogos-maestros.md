# ADR AZ-S1-20 — Catálogos maestros del videojuego

**Issue:** #22 · AZ-S1-20 «Enriquecer y normalizar los catálogos maestros del videojuego» · **Alcance:** capa de datos y datos de referencia.

## Contexto

El esquema anterior de `Videojuego` solo guardaba identidad y presentación
comercial: `titulo`, `descripcion`, `portada`, `fecha_lanzamiento`, categorías,
géneros, actividad y marcas de tiempo. No existían columnas de texto para
desarrolladora, distribuidora, clasificación por edad ni idioma. Por tanto, en
esta tarea **no hubo backfill desde textos legados**: la normalización se aplica
a datos nuevos y a los valores de referencia sembrados.

La auditoría confirmó que ninguna vista, template, admin, reporte, seed o prueba
leía esos atributos como texto libre. El único cambio fuera de
`models`/migraciones/`tests`/`docs` es el admin y el comando de semilla,
autorizados por el issue.

## Decisiones

### 1. Desarrolladora y distribuidora como catálogos M:N

`Desarrolladora` y `Distribuidora` son tablas maestras con:

- `codigo` estable único (slug) para integración y referencias;
- `nombre` único **sin distinguir mayúsculas** mediante
  `UniqueConstraint(Lower("nombre"))`;
- `activo` para retirar un valor sin borrar su historial.

La relación con `Videojuego` es muchos-a-muchos con tablas puente explícitas
(`VideojuegoDesarrolladora`, `VideojuegoDistribuidora`) y
`UniqueConstraint(videojuego, entidad)`. Se descartó una FK única en
`Videojuego` porque un título puede tener varios estudios o varias
distribuidoras por región, y porque una sola columna obligaría a concatenar
valores y perdería la consulta inversa.

### 2. Clasificación por edad como catálogo PEGI

`ClasificacionEdad` almacena el sistema único PEGI: códigos `3`, `7`, `12`,
`16` y `18`, con `nombre` único y `orden` para presentarlos de menor a mayor.
`Videojuego.clasificacion_edad` es una FK **nullable** por
`to_field="codigo"` y `PROTECT`: un título sin clasificación conocida es válido
y no se inventa una edad.

Se descartó guardar una edad numérica libre en `Videojuego` porque permitiría
valores fuera del sistema PEGI y duplicaría la etiqueta visible.

### 3. Idiomas con tipo de presencia

`Idioma` usa el código ISO 639-1 (`es`, `en`, `fr`…) como identificador estable
y `nombre` único sin distinguir mayúsculas. La tabla puente
`VideojuegoIdioma` añade `tipo` (`audio`, `interfaz`, `subtitulos`), restringido
con `CheckConstraint` y con `UniqueConstraint(videojuego, idioma, tipo)`. Un
mismo idioma puede aparecer varias veces en un título si cambia el tipo.

### 4. Sin `Caracteristica` ni atributos técnicos

No se crea un catálogo `Caracteristica` ni campos de requisitos técnicos
(procesador, memoria, almacenamiento, etc.) porque no existe un conjunto de
datos acordado. Añadirlos ahora fijaría un modelo prematuro y difícil de
revertir. Queda como alternativa descartada y posible issue futuro.

### 5. Datos de referencia

La semilla es idempotente y vive en dos lugares con el mismo contenido:

- la migración de datos `catalogo.0014_semilla_catalogos_maestros`;
- el comando `seed_catalogo` (`_seed_clasificaciones_edad`, `_seed_idiomas`).

Se siembran las cinco clasificaciones PEGI y diez idiomas comunes. No se
siembran desarrolladoras ni distribuidoras porque no había datos reales de los
que derivarlas; hacerlo inventaría un catálogo comercial sin respaldo.

## Estrategia de migración

1. `catalogo.0013_catalogos_maestros` (solo esquema): crea los cuatro catálogos,
   las tres tablas puente, los M2M de `Videojuego`, la FK nullable
   `clasificacion_edad` y sus índices.
2. `catalogo.0014_semilla_catalogos_maestros` (solo datos): siembra PEGI e
   idiomas de forma idempotente.

La separación evita mezclar DDL y DML en PostgreSQL. No se editaron migraciones
ya aplicadas.

### Reversión

El esquema anterior no puede representar estos catálogos. Para no perder datos
en silencio, el reverso de `0014` aborta con `RuntimeError` descriptivo si
existe cualquier fila en las tablas puente, si algún `Videojuego` tiene
`clasificacion_edad`, o si hay catálogos fuera de los valores sembrados
(desarrolladoras, distribuidoras, clasificaciones o idiomas personalizados).
Si no hay datos nuevos, elimina solo los valores sembrados y `0013` retira las
tablas.

No se concatena la “primera” desarrolladora/distribuidora al revertir: el
esquema anterior no tiene columnas donde restaurarlas. Abortar es la opción
segura y evita una pérdida silenciosa.

## Garantías de la base de datos

| Regla | Garantía |
|---|---|
| `codigo` único en los cuatro catálogos | `UniqueConstraint` |
| `nombre` único sin mayúsculas en desarrolladora, distribuidora e idioma | `UniqueConstraint(Lower("nombre"))` |
| `nombre` único exacto en clasificación | `UniqueConstraint(nombre)` |
| Pareja/tema duplicada en las puentes | `UniqueConstraint` |
| `tipo` de idioma válido | `CheckConstraint` |
| Clasificación inexistente | FK `PROTECT` a `codigo` |
| Borrado de catálogo en uso | `PROTECT` |
| Borrado del videojuego | `CASCADE` en las puentes |

La base de datos **no** normaliza espacios ni mayúsculas por sí sola: la
unicidad sin mayúsculas se resuelve con `Lower("nombre")`, pero dos nombres que
solo difieren en espacios internos podrían convivir. La regla de carga es
recortar extremos y colapsar espacios con
`catalogo.models.normalizar_nombre_catalogo`, usada por la semilla y las
pruebas.

## Consecuencias y deuda técnica

- `Videojuego` conserva `titulo`, `descripcion`, `portada`,
  `fecha_lanzamiento`, categorías, géneros, actividad y marcas de tiempo. Los
  atributos normalizados viven en catálogos y puentes.
- El admin permite asignar desarrolladoras, distribuidoras e idiomas por
  inline; no se añadieron pantallas nuevas.
- No hay validación de que un idioma tenga sentido para una región ni de
  combinaciones de tipos; es responsabilidad de la carga editorial.
- La semilla no asigna estos catálogos a los videojuegos de ejemplo. Hacerlo
  requeriría datos editoriales reales y queda fuera del alcance.
- Si en el futuro se añade `Caracteristica`, deberá decidirse su granularidad
  (clave/valor, catálogo cerrado o texto) antes de crear tablas.
