# ADR AZ-S1-18 — Roles de usuario normalizados y frontera con permisos de Django

**Estado:** aceptado  
**Fecha:** 2026-11-15  
**Issue:** #20 · AZ-S1-18 «Normalizar asignación de roles y catálogo de permisos de negocio»

## Contexto

`Usuario` tenía una FK directa nullable a un único `Rol` (`cuentas_usuario.rol_id`,
`PROTECT`). Esto impedía asignar varios roles a un usuario y acoplaba la lógica
de negocio al nombre visible del rol (`nombre`), sin un identificador estable.

El issue exige que un usuario pueda tener varios roles y un rol varios usuarios
mediante una tabla puente explícita (`through`), con `UniqueConstraint(usuario,
rol)`, manteniendo `Rol` como catálogo, migrando el rol actual y retirando la FK
directa, sin modificar la autorización de vistas ni el middleware.

## Decisión

### 1. Catálogo de roles

`Rol` incorpora `codigo` (`CharField(max_length=50)`, único, estable) además de
`nombre` (etiqueta visible editable, única), `descripcion` y `activo`. La lógica
de negocio compara por `codigo`, no por la etiqueta.

Roles base (códigos estables): `cliente` (Cliente) y `administrador`
(Administrador). Se garantizan de forma idempotente por migración de datos, por
`seed_catalogo` y por fixture autouse en pruebas (para sobrevivir a `flush`).

### 2. Asignación explícita usuario↔rol

Se crea `UsuarioRol` (`cuentas_usuariorol`) como `through` del M2M
`Usuario.roles`:

- `usuario` FK → `cuentas.Usuario`, `on_delete=CASCADE` (la asignación depende de
  la cuenta).
- `rol` FK → `cuentas.Rol`, `on_delete=PROTECT` (catálogo protegido si está en
  uso).
- `UniqueConstraint(("usuario","rol"), name="cuentas_usuariorol_usuario_rol_unico")`:
  evita asignaciones duplicadas.
- Índice `cuentas_urol_rol_idx` sobre `rol` para búsquedas rol→usuarios. No se
  añade índice duplicado para usuario→roles porque el `UniqueConstraint(usuario,
  rol)` ya lo cubre.
- `related_name="usuarios"` en `Rol` (vía el M2M) se conserva para compatibilidad
  inversa.

**Sin metadatos de auditoría** (`asignado_en`, `asignado_por`, `activo`): no hay
necesidad real actual. Si en el futuro se añade `asignado_por` (FK a usuario),
hará falta declarar `through_fields` en el `ManyToManyField` porque existirían
dos FKs a `cuentas_usuario`.

### 3. Migraciones (esquema y datos separados)

Sin editar migraciones aplicadas, en `cuentas`:

1. `0002` (esquema): añadir `codigo` a `Rol` nullable, sin unique.
2. `0003` (datos): poblar `codigo` con mapeo explícito desde `nombre`;
   `get_or_create` idempotente de roles base; abortar con `RuntimeError` (tabla,
   campo, valor, cantidad de filas) ante nombres sin mapeo o colisiones.
3. `0004` (esquema): `codigo` `NOT NULL` + `UniqueConstraint` `cuentas_rol_codigo_unico`.
4. `0005` (esquema): crear `UsuarioRol` con su `UniqueConstraint` e índice.
5. `0006` (datos): copiar cada `Usuario.rol` no nulo como asignación inicial
   (idempotente); usuarios sin rol quedan sin asignación.
6. `0007` (esquema): `RemoveField(Usuario.rol)` y después `AddField` del M2M
   `roles` (`through=UsuarioRol`, `related_name="usuarios"`, `blank=True`).

La reversión es posible hasta `cuentas.0001_initial` con datos. Si un usuario
tiene varios roles, la reversión restaura **`administrador` si existe; si no, la
asignación de menor PK**. Las asignaciones adicionales **se pierden** porque la
FK monovaluada original no puede representarlas (pérdida documentada en migración
y en este ADR).

### 4. Propiedades de negocio (compatibilidad transitoria)

- `es_cliente`: `True` si el usuario posee el rol `cliente` (aunque tenga otros).
- `es_administrador`: `True` si `is_staff` **o** posee el rol `administrador`.

Ambas se calculan con consultas acotadas (`exists()` sobre `roles`). La inclusión
de `is_staff` en `es_administrador` es una **compatibilidad transitoria** que
conserva el comportamiento previo; se mantiene porque el issue prohíbe cambiar la
autorización de vistas/middleware. Asignar el rol de negocio `administrador` **no**
otorga `is_staff` ni permisos técnicos de Django.

## Frontera entre roles de negocio y permisos técnicos de Django

| Capa | Mecanismo | Propósito | Fuente de verdad |
|---|---|---|---|
| Negocio | `Rol` / `UsuarioRol` (`codigo`) | Funciones del dominio (`cliente`, `administrador`) para reglas de producto. | Catálogo `cuentas_rol` y asignaciones. |
| Técnico (Django auth) | `is_superuser`, `is_staff`, `Group`, `Permission` | Privilegios y acceso administrativo/técnico. | Sistema de autenticación/autorización de Django. |

- **No se replican ni se sincronizan.** `Rol` no sustituye a `is_staff`, `Group` ni
  `Permission`, y estos no crean asignaciones de rol de negocio.
- `createsuperuser` establece `is_staff`/`is_superuser` pero no asigna roles de
  negocio (comportamiento preservado). Un usuario `is_staff`/superuser sin rol de
  negocio no recibe una asignación automática.
- La autorización de vistas/middleware (p. ej. `staff_member_required`, checks de
  `is_staff` en reportes/base) **no se modifica** en este issue.

## Alcance aplicado

- **Modificados (autorizados):** `cuentas/models.py`, migraciones `cuentas/0002`–`0007`,
  `cuentas/forms.py`, `cuentas/admin.py`, `templates/cuentas/perfil.html`,
  `catalogo/management/commands/seed_catalogo.py`, `tests/` (`conftest.py`,
  `test_roles_usuario.py`, `test_migraciones_roles.py`), `docs/`.
- **Sin cambios de autorización:** vistas, decorators, middleware y controles de
  acceso permanecen iguales.

## Deuda técnica

- `es_administrador` depende de `is_staff` por compatibilidad; unificar la
  semántica de “administrador de negocio” con el acceso técnico requiere una
  decisión y cambios de autorización fuera de este alcance.
- Sin metadatos de auditoría en asignaciones; añadir `asignado_por` requerirá
  `through_fields`.
- Tras un `flush`, roles base y catálogos deben resembrarse (fixture autouse en
  tests, `seed_catalogo` idempotente en operación).
- `Usuario.email` sigue sin unicidad (deuda preexistente, fuera de alcance).
