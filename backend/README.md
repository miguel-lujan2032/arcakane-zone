# Arkane Zone — Backend (Django)

Aplicación backend del sistema Arkane Zone. Contiene el modelo de datos, las reglas de negocio, la autenticación, el panel administrativo y la lógica de catálogo, carrito, pedidos, pagos, reportes y soporte.

> **Estado actual:** el backend sigue sirviendo la interfaz con Django Templates + HTMX. La separación definitiva se completará cuando el frontend en Next.js consuma una API JSON. Hoy las rutas existentes devuelven HTML; **todavía no existe una API REST/JSON formal**.

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
├── templates/            # Templates Django (interfaz temporal)
├── tests/                # Pruebas de carrito, pagos, cancelación y autorización
├── manage.py
├── requirements.txt
├── pytest.ini
├── build.sh              # Build de Render
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
| `DATABASE_URL` | Sí | URL de conexión PostgreSQL, por ejemplo `postgres://usuario:clave@host:5432/db`. |
| `DEBUG` | No | `True` en desarrollo; por defecto `False`. |
| `ALLOWED_HOSTS` | No | Lista separada por comas. Por defecto `localhost,127.0.0.1`. |
| `CSRF_TRUSTED_ORIGINS` | No | Orígenes permitidos para CSRF. En Render se agrega automáticamente el host público. |
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
# Dependencias de desarrollo (aún no están declaradas en requirements.txt)
pip install pytest pytest-django

SECRET_KEY=test-key DATABASE_URL=sqlite:///db.sqlite3 DEBUG=True pytest
```

Estado verificado de la suite: **29 pruebas**, todas pasan con `DEBUG=True`.

> **Limitación conocida:** `settings_test.py` hereda `settings.py`; con `DEBUG=False` se activa `SECURE_SSL_REDIRECT` y 14 pruebas de autorización fallan por recibir un `301` en lugar de `302`. Además, `pytest` y `pytest-django` no están en `requirements.txt`. Ambas cosas están registradas como hallazgos del Sprint 1 y deben corregirse en un issue posterior.

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
- **Correo:** `EMAIL_BACKEND` está fijado al backend de consola. El reseteo de contraseña no envía correos reales y los enlaces quedan en los logs. Configurar SMTP antes de habilitar recuperación de contraseña en producción.
- **Proxy HTTPS:** al estar detrás del proxy de Render, se debe validar `SECURE_PROXY_SSL_HEADER` para evitar redirecciones SSL incorrectas.
- **Migraciones:** actualmente se ejecutan durante el build. Evaluar un `preDeployCommand` antes de un despliegue con más de una instancia.
- **Validación:** ejecutar `python manage.py check --deploy` antes de cada despliegue.

## Transición a Next.js

Cuando se implemente el frontend:

1. Definir el contrato de la API (endpoints, serialización y errores).
2. Elegir la estrategia de autenticación (sesión/cookies o tokens) y configurar CORS/CSRF.
3. Exponer endpoints JSON para catálogo, carrito, pedidos, pagos, reportes y soporte.
4. Reemplazar gradualmente `backend/templates/` por las vistas de Next.js.
5. Mantener `/admin/` en Django para la administración interna.

Hasta que ese trabajo exista, este backend debe seguir funcionando como aplicación Django completa.

## Documentación relacionada

- [README principal](../README.md)
- [Auditoría inicial](../docs/audit/INITIAL-AUDIT.md)
- [Plan del Sprint 1](../docs/sprints/SPRINT-1.md)
- [Frontend (pendiente)](../frontend/README.md)
