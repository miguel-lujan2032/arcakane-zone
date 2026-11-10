# Arkane Zone — Backend (API Django)

API REST del sistema Arkane Zone. Contiene el modelo de datos, las reglas de negocio y la autenticación de catálogo, carrito, pedidos, pagos, reportes y soporte.

> **El backend es solo API JSON.** No incluye plantillas, archivos estáticos, HTMX, Tailwind, formularios HTML ni panel administrativo de Django. La interfaz de usuario se implementará en la aplicación Next.js de [`../frontend/`](../frontend/README.md).

## Estructura

```text
backend/
├── arkane_zone/          # Configuración: settings.py, settings_test.py, urls.py, permisos
├── catalogo/             # Categorías, plataformas, géneros y videojuegos
├── cuentas/              # Usuario personalizado, roles y autenticación por token
├── pedidos/              # Carrito, pedidos, detalle y cancelación
├── pagos/                # Pago simulado, pagos y ventas
├── reportes/             # Dashboard y reportes JSON (solo staff)
├── soporte/              # Contacto, solicitud de información y bandeja de contactos
├── tests/                # Pruebas de API y de reglas de negocio
├── manage.py
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── build.sh              # Build de Render
└── .env.example
```

## Requisitos

- Python 3.12 o superior.
- PostgreSQL 14 o superior para un entorno similar a producción.
- `pip` y un entorno virtual.
- Opcional: SQLite para pruebas locales rápidas.

## Configuración local

```bash
cd backend

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Editar .env con valores reales
```

### Variables de entorno

`arkane_zone/settings.py` lee `backend/.env` mediante `django-environ`.

| Variable | Obligatoria | Descripción |
|---|---|---|
| `SECRET_KEY` | Sí | Clave secreta de Django. No debe compartirse ni versionarse. |
| `DATABASE_URL` | Sí | URL de conexión PostgreSQL, por ejemplo `postgres://usuario:clave@host:5432/db`. |
| `DEBUG` | No | `True` en desarrollo; por defecto `False`. |
| `ALLOWED_HOSTS` | No | Lista separada por comas. Por defecto `localhost,127.0.0.1`. |
| `CORS_ALLOWED_ORIGINS` | No | Orígenes permitidos para Next.js. Por defecto `http://localhost:3000,http://127.0.0.1:3000`. |
| `CSRF_TRUSTED_ORIGINS` | No | Orígenes de confianza para CSRF. Se conserva para una futura autenticación por sesión. |
| `RENDER_EXTERNAL_HOSTNAME` | No | La define Render; se agrega a `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`. |
| `AWS_ACCESS_KEY_ID` | No | Si se define, activa almacenamiento S3 para medios. |
| `AWS_SECRET_ACCESS_KEY` | No | Credencial S3. |
| `AWS_STORAGE_BUCKET_NAME` | No | Bucket de medios; por defecto `media`. |
| `AWS_S3_ENDPOINT_URL` | No | Endpoint S3 compatible (por ejemplo, Supabase Storage). |
| `AWS_S3_REGION_NAME` | No | Región S3; por defecto `us-west-2`. |
| `AWS_S3_CUSTOM_DOMAIN` | No | Dominio público del bucket, sin protocolo. |

No se deben subir `.env` ni credenciales al repositorio. El archivo `.env.example` solo contiene placeholders.

### Base de datos y datos iniciales

```bash
python manage.py migrate
python manage.py seed_catalogo
python manage.py createsuperuser   # opcional: usuario staff para la API
```

`seed_catalogo` crea roles, categorías, plataformas, géneros y 15 videojuegos de ejemplo. Es idempotente para los datos que ya existen.

Para un smoke test local con SQLite se puede usar una URL temporal, sin modificar `.env`:

```bash
SECRET_KEY=test-key DATABASE_URL=sqlite:///db.sqlite3 DEBUG=True python manage.py migrate
SECRET_KEY=test-key DATABASE_URL=sqlite:///db.sqlite3 DEBUG=True python manage.py seed_catalogo
```

### Ejecutar el servidor

```bash
python manage.py runserver
```

- API: `http://127.0.0.1:8000/api/v1/`
- Health check: `http://127.0.0.1:8000/api/health/`

No existe `/admin/` ni ninguna interfaz HTML.

## Autenticación

La API usa **TokenAuthentication** de Django REST Framework. El token se obtiene al registrarse o iniciar sesión y se envía en cada petición protegida:

```http
Authorization: Token <tu-token>
```

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "cliente", "password": "mi-clave"}'
```

Respuesta:

```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
  "user": {
    "id": 1,
    "username": "cliente",
    "email": "cliente@example.com",
    "rol": {"id": 1, "nombre": "cliente", "descripcion": ""},
    "is_staff": false
  }
}
```

## Endpoints

### Autenticación y perfil

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `POST` | `/api/v1/auth/register/` | Público | Crea un cliente y devuelve token. |
| `POST` | `/api/v1/auth/login/` | Público | Devuelve token y datos del usuario. |
| `POST` | `/api/v1/auth/logout/` | Autenticado | Elimina el token actual. |
| `GET` | `/api/v1/auth/me/` | Autenticado | Datos del usuario autenticado. |
| `PATCH` | `/api/v1/auth/me/` | Autenticado | Actualiza perfil (nombres, teléfono, dirección, foto). |
| `POST` | `/api/v1/auth/change-password/` | Autenticado | Cambia la contraseña. |

### Catálogo

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/catalogo/videojuegos/` | Público | Lista paginada con filtros. |
| `GET` | `/api/v1/catalogo/videojuegos/<id>/` | Público | Detalle de un videojuego. |
| `POST` | `/api/v1/catalogo/videojuegos/` | Staff | Crea un videojuego. |
| `PUT/PATCH` | `/api/v1/catalogo/videojuegos/<id>/` | Staff | Actualiza un videojuego. |
| `DELETE` | `/api/v1/catalogo/videojuegos/<id>/` | Staff | Elimina un videojuego. |
| `GET/POST` | `/api/v1/catalogo/categorias/` | Público / Staff | Lista o crea categorías. |
| `GET/POST` | `/api/v1/catalogo/plataformas/` | Público / Staff | Lista o crea plataformas. |
| `GET/POST` | `/api/v1/catalogo/generos/` | Público / Staff | Lista o crea géneros. |

Filtros de `videojuegos`: `categoria`, `plataforma`, `genero`, `q` (título), `precio_min`, `precio_max`, `disponible` (`true`/`false`).

### Carrito y pedidos

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/pedidos/carrito/` | Autenticado | Carrito actual (pedido pendiente). |
| `POST` | `/api/v1/pedidos/carrito/items/` | Autenticado | Agrega `{videojuego_id, cantidad}`. |
| `PATCH` | `/api/v1/pedidos/carrito/items/<detalle_id>/` | Autenticado | Cambia `{cantidad}`. |
| `DELETE` | `/api/v1/pedidos/carrito/items/<detalle_id>/` | Autenticado | Elimina el ítem. |
| `GET` | `/api/v1/pedidos/` | Autenticado | Historial paginado (sin carritos vacíos). |
| `GET` | `/api/v1/pedidos/<id>/` | Autenticado | Detalle de un pedido propio. |
| `POST` | `/api/v1/pedidos/<id>/cancelar/` | Autenticado | Cancela un pedido pendiente. |

### Pagos

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `GET` | `/api/v1/pagos/checkout/<pedido_id>/` | Autenticado | Resumen y validación de stock. |
| `POST` | `/api/v1/pagos/procesar/<pedido_id>/` | Autenticado | Ejecuta el pago simulado. |

El pago es **simulado**: no recibe ni almacena datos de tarjeta. La respuesta incluye `aprobado`, `detail`, `pago` y el `pedido` actualizado.

### Reportes (solo staff)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/reportes/dashboard/` | Ventas totales, pedidos por estado y alertas de stock. |
| `GET` | `/api/v1/reportes/ventas/?desde=AAAA-MM-DD&hasta=AAAA-MM-DD` | Ventas con detalle por pedido. |
| `GET` | `/api/v1/reportes/inventario/?filtro=todos` | Inventario filtrado. |
| `GET` | `/api/v1/reportes/videojuegos/` | Catálogo filtrado con opciones para la UI. |

Filtros de inventario: `todos`, `agotados`, `bajo_stock`, `disponibles`, `inactivos`.

Filtros de videojuegos: `categoria`, `genero`, `plataforma`, `estado` (`activo`/`inactivo`), `disponibilidad` (`disponible`/`agotado`).

### Soporte

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `POST` | `/api/v1/soporte/contacto/` | Público | Envía un mensaje de contacto. |
| `POST` | `/api/v1/soporte/mayor-informacion/` | Público | Solicitud de información. |
| `GET` | `/api/v1/soporte/contactos/` | Staff | Bandeja paginada de contactos. |
| `PATCH` | `/api/v1/soporte/contactos/<id>/` | Staff | Marca `{atendido: true}`. |

### Formato de respuestas

- Las listas usan paginación de DRF (20 por página):

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": []
}
```

- Los errores de validación devuelven `400` con el detalle por campo.
- `401` indica que falta autenticación o el token es inválido.
- `403` indica que el usuario no tiene permisos.
- `404` indica que el recurso no existe o no pertenece al usuario.

## Pruebas

La suite usa `arkane_zone/settings_test.py`, que configura SQLite en memoria, hashing rápido de contraseñas y desactiva las redirecciones SSL.

```bash
pip install -r requirements-dev.txt
pytest
```

`settings_test.py` define valores por defecto para `SECRET_KEY`, `DATABASE_URL` y `DEBUG`, por lo que no hace falta un `.env` para ejecutar las pruebas.

Estado verificado: **73 pruebas**, todas pasan.

Cobertura por archivo:

| Archivo | Contenido |
|---|---|
| `tests/test_api.py` | Endpoints de auth, catálogo, carrito, pedidos, pagos, soporte y reportes. |
| `tests/test_autorizacion.py` | Permisos públicos, autenticados y staff. |
| `tests/test_carrito.py` | Reglas de negocio del carrito y stock. |
| `tests/test_pagos.py` | Pago aprobado, rechazado y stock. |
| `tests/test_cancelacion.py` | Cancelación de pedidos. |

## Despliegue en Render

El blueprint está en la raíz del repositorio: [`../render.yaml`](../render.yaml).

- `rootDir: backend`: Render ejecuta los comandos dentro de esta carpeta.
- Build: `./build.sh`.
  - Instala `requirements.txt`.
  - Ejecuta `migrate`.
- Start: `gunicorn arkane_zone.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`.
- Health check: `/api/health/`.
- Variables sensibles: `SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` se configuran manualmente en Render (`sync: false`).

### Consideraciones de producción

- **Medios:** si no se configuran las variables `AWS_*`, las portadas y fotos se guardan en el sistema de archivos local de Render, que es efímero. Además, `/media/` solo se sirve con `DEBUG=True`. Para producción se debe configurar S3/Supabase Storage.
- **Proxy HTTPS:** Render termina TLS en su proxy. `SECURE_PROXY_SSL_HEADER` ya está configurado para que Django reconozca `https`.
- **CORS:** configurar `CORS_ALLOWED_ORIGINS` con el dominio real del frontend Next.js.
- **Migraciones:** actualmente se ejecutan durante el build. Evaluar un `preDeployCommand` antes de un despliegue con más de una instancia.
- **Validación:** ejecutar `python manage.py check --deploy` antes de cada despliegue.
- **Administración:** no existe panel `/admin/`. Los usuarios staff gestionan el catálogo, los contactos y los reportes a través de la API.

## Documentación relacionada

- [README principal](../README.md)
- [Frontend Next.js (pendiente)](../frontend/README.md)
- [Auditoría inicial](../docs/audit/INITIAL-AUDIT.md)
- [Plan del Sprint 1](../docs/sprints/SPRINT-1.md)
