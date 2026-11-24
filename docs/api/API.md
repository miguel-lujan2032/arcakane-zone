# API REST de Arcakane Zone

API JSON versionada que expone los recursos del sistema sin reemplazar la
interfaz HTML existente. El sitio con Django Templates + HTMX sigue disponible
en sus rutas de siempre.

- **Base:** `/api/v1/`
- **Raíz navegable:** `GET /api/v1/` (devuelve las URLs de todos los recursos)
- **Salud:** `GET /api/v1/health/`
- **Formato:** JSON con UTF-8 y barra final obligatoria en las rutas.
- **Postman:** [`Arcakane_Zone.postman_collection.json`](./Arcakane_Zone.postman_collection.json)
  incluye todos los endpoints con credenciales demo y variables automáticas.

`/api/` redirige a `/api/v1/` y `/api/catalogo/` redirige a
`/api/v1/catalogo/videojuegos/` por compatibilidad.

El contrato v1 es aditivo: tras la normalización del modelo se añadieron campos
y se conservaron todos los existentes. Los campos históricos marcados como
*deprecated* siguen devolviendo un único valor determinista; las listas nuevas
son la forma preferida. El sobre de respuesta y los códigos HTTP de esta guía
no cambian.

## Autenticación y autorización

La API acepta dos mecanismos:

1. **Token de DRF**

   ```http
   Authorization: Token <token>
   ```

   El token se obtiene en `POST /api/v1/auth/login/` o
   `POST /api/v1/auth/registro/`.

2. **Sesión/cookie de Django**

   Es la misma sesión del sitio HTML y del admin. Para peticiones que modifican
   datos hay que enviar la cookie `csrftoken` en la cabecera `X-CSRFToken`.
   `GET /api/v1/auth/csrf/` garantiza la creación de la cookie.

| Recurso | Acceso |
|---|---|
| Catálogo (categorías, plataformas, géneros, videojuegos, ofertas) | Lectura pública; escritura solo administrador |
| Carrito, pedidos, pagos | Usuario autenticado; dueño del recurso o administrador |
| Ventas, reportes, usuarios y roles | Solo administrador |
| Contacto | Creación pública; lectura de los propios mensajes o todos para administrador |
| Solicitud de información | Pública |

Se considera administrador al usuario con `is_staff=True` o con el rol de
negocio `administrador`.

## Sobre de respuesta

### Éxito

```json
{
  "success": true,
  "data": {},
  "message": "Texto opcional",
  "pagination": {
    "count": 15,
    "page": 1,
    "page_size": 20,
    "total_pages": 1,
    "next": null,
    "previous": null
  }
}
```

`message` y `pagination` solo aparecen cuando aplican.

### Error

```json
{
  "success": false,
  "error": {
    "code": "datos_invalidos",
    "message": "Datos de entrada inválidos.",
    "details": {
      "email": ["Este campo es obligatorio."]
    }
  }
}
```

`details` es opcional y contiene los errores por campo o información adicional.

## Límites de solicitudes y bloqueo de login

Las respuestas `429` usan el sobre estándar con
`error.code = demasiadas_solicitudes` e incluyen **siempre** la cabecera
`Retry-After` con los segundos que faltan para reintentar.

| Scope | Aplica a | Tasa por defecto | Clave |
|---|---|---|---|
| `anon` | Peticiones de visitantes | `100/min` | IP |
| `user` | Peticiones autenticadas | `1000/hour` | Usuario |
| `login` | `POST /auth/login/` | `10/min` | IP |
| `registro` | `POST /auth/registro/` | `5/hour` | IP |
| `contacto` | Creación de contactos y solicitudes de información | `5/hour` | IP |
| `password_reset` | Solicitud y confirmación de restablecimiento | `5/hour` | IP |

Ejemplo de respuesta `429`:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 37
Content-Type: application/json
```

```json
{
  "success": false,
  "error": {
    "code": "demasiadas_solicitudes",
    "message": "Se superó el límite de solicitudes. Intenta más tarde."
  }
}
```

Además, `POST /auth/login/` bloquea temporalmente tras
`LOGIN_MAX_FAILED_ATTEMPTS` (5) credenciales incorrectas (`401`) en
`LOGIN_FAILURE_WINDOW_SECONDS` (900 s). El intento siguiente devuelve `429`
con `Retry-After` hasta que pasa `LOGIN_LOCKOUT_SECONDS` (900 s). Durante el
bloqueo **no se verifica la contraseña**. La clave es un hash de
`usuario en minúsculas + IP`: ni la contraseña ni los datos del usuario se
guardan en caché. Un login correcto reinicia el contador; los errores de
validación (`400`) no cuentan como intentos fallidos.

La IP se toma de `REMOTE_ADDR` por defecto. `X-Forwarded-For` solo se usa
cuando `THROTTLE_NUM_PROXIES > 0` (número de proxies propios delante de
Django); con `0`, una cabecera falsificada no puede cambiar la clave.

| HTTP | `code` habitual | Cuándo ocurre |
|---|---|---|
| `400` | `datos_invalidos` | Validación de entrada |
| `400` | `token_invalido` | Enlace de restablecimiento inválido o vencido |
| `401` | `no_autenticado` / `credenciales_invalidas` | Falta autenticación o login incorrecto |
| `402` | `pago_rechazado` | La pasarela simulada rechazó el pago |
| `403` | `permiso_denegado` | El usuario no tiene el rol requerido |
| `404` | `no_encontrado` | El recurso no existe o no pertenece al usuario |
| `405` | `metodo_no_permitido` | Método HTTP no soportado |
| `409` | `conflicto` | Regla de negocio o restricción de integridad |
| `429` | `demasiadas_solicitudes` | Límite de solicitudes superado o login bloqueado |
| `500` | `error_interno` | Error no controlado (siempre en JSON) |

## Listados: paginación, búsqueda y orden

- Paginación por páginas: `?page=2&page_size=50` (máximo `100`, por defecto `20`).
- Búsqueda de texto: `?q=zelda` (catálogo y usuarios).
- Orden: `?ordering=titulo` o `?ordering=-precio_vigente` según los campos
  permitidos de cada recurso.

## Endpoints

### Autenticación y perfil

| Método | Ruta | Cuerpo / notas |
|---|---|---|
| `POST` | `/api/v1/auth/registro/` | `username`, `email`, `password`, `password_confirm` y datos opcionales |
| `POST` | `/api/v1/auth/login/` | `username`, `password` |
| `POST` | `/api/v1/auth/logout/` | Invalida el token presentado y cierra la sesión |
| `GET` | `/api/v1/auth/csrf/` | Devuelve `csrfToken` y crea la cookie |
| `GET` | `/api/v1/auth/me/` | Perfil del usuario autenticado |
| `PATCH`/`PUT` | `/api/v1/auth/me/` | Actualiza el perfil |
| `POST` | `/api/v1/auth/me/password/` | `old_password`, `new_password`, `new_password_confirm` |
| `POST` | `/api/v1/auth/password-reset/` | `email`; siempre `200` neutro |
| `POST` | `/api/v1/auth/password-reset/confirm/` | `uid`, `token`, `new_password`, `new_password_confirm` |

Respuesta de login y registro:

```json
{
  "success": true,
  "data": {
    "usuario": { "id": 1, "username": "cliente", "...": "..." },
    "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
  },
  "message": "Sesión iniciada correctamente."
}
```

### Recuperación de contraseña

Solicitud (`POST /api/v1/auth/password-reset/`):

```http
POST /api/v1/auth/password-reset/
Content-Type: application/json

{"email": "cliente@test.com"}
```

Siempre devuelve `200` con el mismo sobre, exista o no la cuenta:

```json
{
  "success": true,
  "data": null,
  "message": "Si la cuenta existe y está activa, enviamos un enlace para restablecer la contraseña."
}
```

Solo se envía correo a cuentas activas con contraseña utilizable (una por
cuenta si varias comparten el correo). Un correo con formato inválido sí da
`400 datos_invalidos`. El enlace usa `FRONTEND_BASE_URL` más
`PASSWORD_RESET_FRONTEND_PATH`; por defecto:
`http://localhost:5173/restablecer-contrasena/{uid}/{token}`. El frontend debe
tomar `uid` y `token` de la ruta y enviarlos a la confirmación.

Confirmación (`POST /api/v1/auth/password-reset/confirm/`):

```http
POST /api/v1/auth/password-reset/confirm/
Content-Type: application/json

{
  "uid": "MQ",
  "token": "c1e9bc-abc...",
  "new_password": "NuevaClave#2026",
  "new_password_confirm": "NuevaClave#2026"
}
```

- Éxito: `200`, sobre estándar y
  `"message": "Contraseña restablecida correctamente."`. No inicia sesión y
  revoca los tokens de API previos del usuario.
- `uid` inválido, token manipulado o vencido: `400 token_invalido`, sin
  distinguir la causa.
- Contraseña débil o distinta de la confirmación: `400 datos_invalidos` con
  `error.details` en `new_password` o `new_password_confirm`.

El token es el generador estándar de Django: **un solo uso** (deja de valer al
cambiar la contraseña) y vence a los `PASSWORD_RESET_TIMEOUT` segundos
(`3600` por defecto, ~60 minutos). Ambos endpoints comparten el scope
`password_reset` (`5/hour` por IP, `THROTTLE_RATE_PASSWORD_RESET`): al
superarlo devuelven `429` con `Retry-After`. Además hay un tope silencioso de
`PASSWORD_RESET_MAX_EMAILS_PER_HOUR` envíos por correo normalizado (`3` por
defecto): al alcanzarse se sigue respondiendo el mismo `200` pero no se envía
correo. El SMTP se configura con `EMAIL_*` y `DEFAULT_FROM_EMAIL`; sin
`EMAIL_HOST` se usa el backend de consola en desarrollo.

### Catálogo

| Método | Ruta | Notas |
|---|---|---|
| `GET` | `/api/v1/catalogo/categorias/` | `q`, `ordering`, `activo` (admin) |
| `GET` | `/api/v1/catalogo/plataformas/` | Igual que categorías |
| `GET` | `/api/v1/catalogo/generos/` | Igual que categorías |
| `GET` | `/api/v1/catalogo/videojuegos/` | `q`, `categoria`, `genero`, `plataforma`, `disponible`, `activo`, `ordering` |
| `GET` | `/api/v1/catalogo/videojuegos/{id}/` | Detalle con ofertas |
| `GET` | `/api/v1/catalogo/videojuegos/{id}/ofertas/` | Ofertas publicadas del título |
| `GET` | `/api/v1/catalogo/ofertas/` | `q`, `videojuego`, `plataforma`, `categoria`, `genero`, `disponible`, `estado_publicacion` (admin), `ordering` |
| `POST`/`PUT`/`PATCH`/`DELETE` | `/api/v1/catalogo/...` | Solo administrador |

Los filtros `categoria`, `genero` y `plataforma` conservan su nombre y
semántica. Los dos primeros consultan ahora relaciones muchos-a-muchos y se
aplica `distinct()` para no duplicar resultados ni romper la paginación.

Ejemplo de videojuego con los campos aditivos:

```json
{
  "id": 1,
  "titulo": "Juego Alpha",
  "categoria": 3,
  "categoria_nombre": "Acción",
  "categorias": [3, 7],
  "genero": 5,
  "genero_nombre": "RPG",
  "generos": [5, 9],
  "activo": true,
  "disponible": true
}
```

`categoria`, `categoria_nombre`, `genero` y `genero_nombre` están *deprecated*:
se conservan por compatibilidad y exponen el primero por nombre de las listas
`categorias`/`generos`, cuyos IDs también se ordenan por nombre. La escritura
acepta la forma histórica (`categoria` o `genero`) y las listas nuevas; si se
envían ambas, prevalecen las listas.

### Carrito

| Método | Ruta | Cuerpo |
|---|---|---|
| `GET` | `/api/v1/carrito/` | Carrito pendiente del usuario (vacío si no existe) |
| `DELETE` | `/api/v1/carrito/` | Vacía el carrito |
| `POST` | `/api/v1/carrito/items/` | `{ "oferta": 1, "cantidad": 2 }` |
| `GET` | `/api/v1/carrito/items/{id}/` | Detalle de una línea |
| `PATCH` | `/api/v1/carrito/items/{id}/` | `{ "cantidad": 3 }`; `0` elimina la línea |
| `DELETE` | `/api/v1/carrito/items/{id}/` | Elimina la línea |

### Pedidos

| Método | Ruta | Notas |
|---|---|---|
| `GET` | `/api/v1/pedidos/` | Pedidos del usuario; admin ve todos |
| `GET` | `/api/v1/pedidos/{id}/` | Detalle con líneas, pago y venta |
| `PATCH` | `/api/v1/pedidos/{id}/` | `{ "estado": "cancelado" }` |
| `POST` | `/api/v1/pedidos/{id}/cancelar/` | Alias explícito de cancelación |

Solo se permite cancelar pedidos en estado `pendiente`; cualquier otra
transición devuelve `409 Conflict`. Los textos de `estado` (`pendiente`,
`pagado`, `cancelado`) no cambian: ahora se leen del `codigo` del catálogo de
estados. El detalle incluye `pago` —el intento aprobado, o `null` si no lo
hay— y la lista aditiva `intentos_pago` con todos los intentos.

### Pagos y ventas

| Método | Ruta | Notas |
|---|---|---|
| `GET` | `/api/v1/pagos/` | Pagos propios; admin ve todos |
| `GET` | `/api/v1/pagos/{id}/` | Detalle |
| `POST` | `/api/v1/pagos/` | `{ "pedido": 1 }`; procesa el pago simulado |
| `GET` | `/api/v1/ventas/` | Solo administrador; filtros `desde`, `hasta`, `cliente` |

Un pago rechazado devuelve `402 Payment Required` con el registro del intento en
`error.details`. El pedido permanece pendiente y el pago puede reintentarse; un
rechazo ya no bloquea los intentos posteriores. Con varios intentos para el
mismo pedido, `POST /pagos/` devuelve el último (el aprobado cuando el pago se
completó): `monto` conserva su nombre histórico y se mapea desde
`IntentoPago.importe`, mientras el pedido expone el aprobado en `pago` y todos
en `intentos_pago`. Los textos de `estado` (`aprobado`, `rechazado`,
`pendiente`) también provienen del `codigo` del catálogo.

### Reportes (solo administrador)

| Método | Ruta | Filtros |
|---|---|---|
| `GET` | `/api/v1/reportes/dashboard/` | — |
| `GET` | `/api/v1/reportes/ventas/` | `desde`, `hasta`, `cliente`, paginación |
| `GET` | `/api/v1/reportes/inventario/` | `filtro=todos\|agotados\|bajo_stock\|disponibles\|inactivas` |
| `GET` | `/api/v1/reportes/videojuegos/` | `categoria`, `genero`, `plataforma`, `estado`, `disponibilidad` |

Los reportes paginados devuelven `data.resultados` junto con `resumen`. Los
filtros `categoria`/`genero` usan las relaciones muchos-a-muchos con
`distinct()`, de modo que un videojuego con varias categorías no duplica
ofertas paginadas. El dashboard y `seed_catalogo` emplean las mismas tablas
normalizadas sin alterar sus respuestas.

### Soporte

| Método | Ruta | Notas |
|---|---|---|
| `GET` | `/api/v1/soporte/contactos/` | Propios; admin ve todos |
| `POST` | `/api/v1/soporte/contactos/` | Público. Usuarios autenticados pueden omitir `nombre` y `email` |
| `GET`/`PATCH`/`DELETE` | `/api/v1/soporte/contactos/{id}/` | Dueño (lectura) o administrador |
| `POST` | `/api/v1/soporte/mayor-informacion/` | `nombre`, `email`, `telefono` opcional |

### Usuarios y roles (solo administrador)

| Método | Ruta | Filtros |
|---|---|---|
| `GET` | `/api/v1/usuarios/` | `q`, `rol`, `activo`, `ordering` |
| `GET` | `/api/v1/usuarios/{id}/` | Detalle |
| `GET` | `/api/v1/roles/` | Listado completo |

Usuarios y roles son de solo lectura a través de la API; su gestión sigue en el
admin de Django. `rol` y `rol_nombre` se conservan: `rol` es el primer ID por
nombre de `Usuario.roles` y `rol_nombre` es el `codigo` estable (`cliente`,
`administrador`), que mantiene el texto histórico de la API. La lista aditiva
`roles` expone todos los IDs ordenados por nombre; `/roles/` añade el campo
`codigo` y su `nombre` devuelve ese mismo código. Las propiedades de negocio
`es_administrador`/`es_cliente` siguen intactas y gobiernan los permisos.

## Ejemplos

### Login con token y consulta del catálogo

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"cliente","password":"secreto"}'

curl -s http://localhost:8000/api/v1/catalogo/videojuegos/?q=zelda
```

### Pago con token

```bash
curl -s -X POST http://localhost:8000/api/v1/pagos/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"pedido": 12}'
```

### Uso desde el frontend

El cliente TypeScript está en
[`frontend/src/api/client.ts`](../../frontend/src/api/client.ts).

```ts
import { auth, catalogo, setAuthToken } from "./api/client";

const { token } = await auth.login("cliente", "secreto");
setAuthToken(token);

const { data, pagination } = await catalogo.videojuegos({ q: "zelda", page: 1 });
console.log(data, pagination?.count);
```

## Pruebas

```bash
cd backend
SECRET_KEY=test-key DATABASE_URL=sqlite:///db.sqlite3 DEBUG=True \
  .venv/bin/python -m pytest -q
```

Las pruebas específicas de la API están en:

- `tests/test_api_catalogo.py`
- `tests/test_api_auth.py`
- `tests/test_api_carrito_pedidos_pagos.py`
- `tests/test_api_reportes_soporte.py`
- `tests/test_api_usuarios_ventas.py`
- `tests/test_api_contrato_modelo_normalizado.py`

## Compatibilidad con el sitio HTML

Las rutas HTML (`/catalogo/`, `/pedidos/`, `/pagos/`, `/soporte/`, `/admin/`,
etc.) no cambian. La API reutiliza los mismos modelos, servicios y reglas de
negocio; no existe una segunda implementación de la lógica.
