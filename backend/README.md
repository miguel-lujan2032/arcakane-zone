# Arcakane Zone — Backend (Django)

Aplicación backend del sistema Arcakane Zone. Contiene el modelo de datos, las reglas de negocio, la autenticación, el panel administrativo y la lógica de catálogo, carrito, pedidos, pagos, reportes y soporte.

> **Estado actual:** el backend sirve la interfaz existente con Django Templates + HTMX **y** una API REST/JSON versionada en `/api/v1/`. Ambas capas comparten modelos, servicios, permisos y reglas de negocio. La documentación del contrato está en [`docs/api/API.md`](../docs/api/API.md).

## Docker

El backend forma parte del stack Docker Compose definido en la raíz del repositorio. Para levantar todo (PostgreSQL, backend, frontend y pgAdmin):

```bash
cp .env.example .env      # en la raíz del repositorio
# editar secretos
docker compose up -d --build
```

La guía completa —variables, puertos, migraciones, superusuario, logs, respaldos y diferencias entre desarrollo y producción— está en el [README principal](../README.md).

Archivos relevantes de esta carpeta:

- `Dockerfile`: imagen de producción basada en `python:3.12.9-slim`, usuario no privilegiado y Gunicorn por defecto.
- `.dockerignore`: excluye `.env`, `.venv`, pruebas, medios y estáticos locales del contexto de build.
- `docker/entrypoint.sh`: espera a PostgreSQL, crea la tabla de caché si hace falta, aplica migraciones, recolecta estáticos y opcionalmente ejecuta `seed_catalogo`.

Comandos habituales dentro del contenedor:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py seed_catalogo
docker compose exec backend python manage.py shell
```

### Throttling y caché

Los límites de la API (`anon`, `user`, `login`, `registro`, `contacto`,
`password_reset`) se
guardan en caché. Por defecto se usa la tabla `django_cache` de PostgreSQL;
el entrypoint la crea con `python manage.py createcachetable` de forma
idempotente. Para usar Redis, define `REDIS_URL` (requiere el paquete `redis`).
Las tasas y el bloqueo de login se configuran con las variables
`THROTTLE_RATE_*`, `THROTTLE_NUM_PROXIES` y `LOGIN_*` documentadas en
[`.env.example`](.env.example) y en [`docs/api/API.md`](../docs/api/API.md).

## Estructura

```text
backend/
├── arkane_zone/          # Configuración: settings.py, settings_test.py, urls.py, wsgi.py, asgi.py
├── catalogo/             # Categorías, plataformas, géneros y videojuegos
├── cuentas/              # Usuario personalizado, roles, registro y perfil
├── pedidos/              # Carrito, pedidos, detalle y cancelación
├── pagos/                # Pago simulado, pagos y ventas
├── reportes/             # Dashboard y reportes (solo staff)
├── soporte/              # Contacto, solicitud de información y ayuda
├── api/                  # API REST: serializers, vistas, rutas, permisos y errores
├── templates/            # Templates Django (interfaz HTML)
├── tests/                # Pruebas de API, carrito, pagos, cancelación y autorización
├── manage.py
├── requirements.txt
├── pytest.ini
├── build.sh              # Build de Render
├── Dockerfile            # Imagen para Docker Compose
├── .dockerignore
├── docker/
│   └── entrypoint.sh     # Espera DB, migra, recolecta estáticos y arranca
└── .env.example
```

## Requisitos

- Python 3.12 o superior.
- PostgreSQL 14 o superior para un entorno similar a producción.
- `pip` y un entorno virtual.
- Opcional: SQLite para pruebas locales rápidas o smoke tests.

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
| `DATABASE_URL` | Condicional | URL de conexión PostgreSQL, por ejemplo `postgres://usuario:clave@host:5432/db`. Si no se define, se usan las variables `POSTGRES_*`. |
| `POSTGRES_DB` | Condicional | Nombre de la base de datos cuando se usa el fallback de Docker Compose. |
| `POSTGRES_USER` | Condicional | Usuario de PostgreSQL cuando se usa el fallback de Docker Compose. |
| `POSTGRES_PASSWORD` | Condicional | Contraseña de PostgreSQL cuando se usa el fallback de Docker Compose. |
| `POSTGRES_HOST` | No | Host de PostgreSQL; por defecto `db` en Docker. |
| `POSTGRES_PORT` | No | Puerto de PostgreSQL; por defecto `5432`. |
| `DEBUG` | No | `True` en desarrollo; por defecto `False`. |
| `ALLOWED_HOSTS` | No | Lista separada por comas. Por defecto `localhost,127.0.0.1,backend`. |
| `CSRF_TRUSTED_ORIGINS` | No | Orígenes permitidos para CSRF. En Render se agrega automáticamente el host público. |
| `CORS_ALLOWED_ORIGINS` | No | Orígenes permitidos para CORS (lista separada por comas). Solo hace falta si el frontend llama a la API sin el proxy `/api`. |
| `EMAIL_BACKEND` | No | Por defecto, consola en desarrollo; se usa SMTP automáticamente si se define `EMAIL_HOST`. |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | No | Servidor SMTP. `EMAIL_PORT` por defecto `25`. |
| `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, `EMAIL_TIMEOUT` | No | Opciones SMTP; TLS/SSL en `False` y tiempo de espera `10` s por defecto. |
| `DEFAULT_FROM_EMAIL` | No | Remitente de los correos de restablecimiento. |
| `PASSWORD_RESET_TIMEOUT` | No | Segundos de validez del enlace; `3600` por defecto. |
| `FRONTEND_BASE_URL`, `PASSWORD_RESET_FRONTEND_PATH` | No | Base y patrón del enlace del correo; defecto `http://localhost:5173` + `/restablecer-contrasena/{uid}/{token}`. |
| `PASSWORD_RESET_MAX_EMAILS_PER_HOUR` | No | Máximo de correos por hora y correo normalizado; `3` por defecto. |
| `SECURE_SSL_REDIRECT` | No | Fuerza HTTPS cuando `DEBUG=False`; por defecto `True`. En Docker se pone `False` porque TLS termina en el proxy. |
| `USE_X_FORWARDED_HOST` | No | Usa `X-Forwarded-Host` detrás de un proxy; por defecto `False`. |
| `RENDER_EXTERNAL_HOSTNAME` | No | La define Render; se agrega a `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`. |
| `AWS_ACCESS_KEY_ID` | No | Si se define, activa almacenamiento S3 para medios. |
| `AWS_SECRET_ACCESS_KEY` | No | Credencial S3. |
| `AWS_STORAGE_BUCKET_NAME` | No | Bucket de medios; por defecto `media`. |
| `AWS_S3_ENDPOINT_URL` | No | Endpoint S3 compatible (por ejemplo, Supabase Storage). |
| `AWS_S3_REGION_NAME` | No | Región S3; por defecto `us-west-2`. |
| `AWS_S3_CUSTOM_DOMAIN` | No | Dominio público del bucket, sin protocolo. |

No se deben subir `.env` ni credenciales al repositorio. El archivo `.env.example` solo contiene placeholders.

### Base de datos y datos iniciales

Con PostgreSQL configurado en `DATABASE_URL`:

```bash
python manage.py migrate
python manage.py seed_catalogo
python manage.py createsuperuser
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

- Aplicación: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

## Pruebas

La suite usa `arkane_zone/settings_test.py`, que cambia la base de datos a SQLite en memoria y usa hashing rápido de contraseñas.

```bash
# Dependencias de desarrollo y pruebas
pip install -r requirements-dev.txt

SECRET_KEY=test-key DATABASE_URL=sqlite:///db.sqlite3 DEBUG=True pytest
```

Estado verificado de la suite: **130 pruebas**, todas pasan. Incluye pruebas de
la API REST (`tests/test_api_*.py`) y las pruebas originales de la interfaz HTML.

`settings_test.py` fuerza `DEBUG=True`, desactiva las redirecciones HTTPS y usa
SQLite en memoria, por lo que la suite es independiente del entorno.

## Rutas principales

| Ruta | Descripción |
|---|---|
| `/` y `/catalogo/` | Catálogo con filtros por categoría, plataforma, género y búsqueda |
| `/catalogo/<id>/` | Detalle de videojuego |
| `/cuentas/registro/` | Registro de clientes |
| `/cuentas/login/` | Inicio de sesión (auth de Django) |
| `/cuentas/perfil/` | Perfil del usuario autenticado |
| `/cuentas/perfil/cambiar-password/` | Cambio de contraseña |
| `/pedidos/carrito/` | Carrito del usuario |
| `/pedidos/mis-pedidos/` | Historial de pedidos |
| `/pedidos/<id>/` | Detalle de pedido |
| `/pagos/checkout/<pedido_id>/` | Resumen previo al pago |
| `/pagos/procesar/<pedido_id>/` | Procesamiento del pago simulado |
| `/reportes/*` | Dashboard, ventas, inventario y videojuegos (solo staff) |
| `/soporte/contacto/` | Formulario de contacto |
| `/soporte/mayor-informacion/` | Solicitud de información |
| `/soporte/ayuda/` | Centro de ayuda |
| `/admin/` | Panel administrativo con django-unfold |

## API REST

- **Base:** `/api/v1/` (raíz navegable en `GET /api/v1/`).
- **Salud:** `GET /api/v1/health/`.
- **Autenticación:** token de DRF (`Authorization: Bearer <token>`) o sesión de
  Django con `X-CSRFToken`.
- **Respuestas:** sobre uniforme `{"success": true, "data": ...}` y errores
  `{"success": false, "error": {"code", "message", "details"}}`.
- **Paginación:** `?page=1&page_size=20`; búsqueda `?q=`; orden `?ordering=`.

Recursos principales: catálogo, carrito, pedidos, pagos, ventas, reportes,
soporte, usuarios y roles. El detalle de rutas, cuerpos y códigos de estado está
en [`docs/api/API.md`](../docs/api/API.md).

```bash
# Token
curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"cliente","password":"secreto"}'

# Catálogo público
curl -s "http://localhost:8000/api/v1/catalogo/videojuegos/?q=zelda"
```

La API y el sitio HTML comparten servicios, por lo que una regla de negocio
(cancelación, checkout, descuento de stock) se comporta igual por ambas vías.

## Despliegue en Render

El blueprint está en la raíz del repositorio: [`../render.yaml`](../render.yaml).

- `rootDir: backend`: Render ejecuta los comandos dentro de esta carpeta.
- Build: `./build.sh`.
  - Instala `requirements.txt`.
  - Ejecuta `collectstatic --no-input`.
  - Ejecuta `migrate`.
- Start: `gunicorn arkane_zone.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`.
- Estáticos: WhiteNoise con `CompressedManifestStaticFilesStorage`.
- Variables sensibles: `SECRET_KEY`, `DATABASE_URL` y `ALLOWED_HOSTS` se configuran manualmente en Render (`sync: false`).

### Consideraciones de producción

- **Medios:** si no se configuran las variables `AWS_*`, las portadas y fotos se guardan en el sistema de archivos local de Render, que es efímero. Además, `/media/` solo se sirve con `DEBUG=True`. Para producción se debe configurar S3/Supabase Storage o aceptar explícitamente la limitación.
- **Correo:** sin `EMAIL_HOST` se usa el backend de consola, así que en desarrollo los enlaces se imprimen en la terminal (se puede probar con `pytest`, que usa `locmem`). En producción configura `EMAIL_*` y `DEFAULT_FROM_EMAIL`; de lo contrario la recuperación por API no enviará correos reales.
- **Proxy HTTPS:** `SECURE_PROXY_SSL_HEADER` está configurado para confiar en `X-Forwarded-Proto`. En Docker, `SECURE_SSL_REDIRECT` se desactiva dentro del contenedor porque TLS termina en el proxy inverso; el healthcheck interno usa HTTP.
- **Migraciones:** actualmente se ejecutan durante el build. Evaluar un `preDeployCommand` antes de un despliegue con más de una instancia.
- **Validación:** ejecutar `python manage.py check --deploy` antes de cada despliegue.

## Convivencia con el frontend

La API está disponible para que el frontend React consuma los recursos de forma
desacoplada, mientras las plantillas HTML siguen funcionando como respaldo y
para el panel administrativo:

1. El frontend usa `/api/v1/...` mediante el proxy de Vite/Nginx, sin CORS en
   el flujo normal.
2. Los clientes externos pueden autenticarse con token de DRF.
3. La administración interna permanece en `/admin/` con django-unfold.
4. Las plantillas se pueden retirar gradualmente sin tocar la lógica de negocio.

## Documentación relacionada

- [README principal](../README.md)
- [API REST](../docs/api/API.md)
- [Auditoría inicial](../docs/audit/INITIAL-AUDIT.md)
- [Plan del Sprint 1](../docs/sprints/SPRINT-1.md)
- [Frontend](../frontend/README.md)
