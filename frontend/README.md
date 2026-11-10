# Arkane Zone — Frontend (Next.js)

Aplicación de interfaz de usuario para Arkane Zone. **Esta carpeta es un placeholder:** el frontend todavía no está implementado. El backend ya es una API JSON funcional y está documentado en [`../backend/README.md`](../backend/README.md).

El objetivo es construir aquí una aplicación independiente con **Next.js** que consuma la API del backend.

## Estado

| Elemento | Estado |
|---|---|
| Aplicación Next.js | No creada |
| Contrato de API | Disponible en `/api/v1/` (ver [`../backend/README.md`](../backend/README.md)) |
| Autenticación | Token de DRF (`Authorization: Token <token>`) |
| Diseño de UI | Por definir |
| Despliegue | Por definir |

## Stack propuesto

- Next.js con App Router.
- TypeScript.
- Tailwind CSS.
- ESLint.
- Variables de entorno públicas con prefijo `NEXT_PUBLIC_`.

La versión exacta de Next.js y las dependencias se fijarán al crear la aplicación, para evitar un `package.json` prematuro sin implementación.

## Estructura propuesta

```text
frontend/
├── src/
│   ├── app/                 # Rutas y layouts (App Router)
│   ├── components/          # Componentes reutilizables
│   ├── features/            # Módulos por dominio: catálogo, carrito, pedidos, pagos, cuenta, soporte
│   ├── lib/                 # Cliente HTTP, utilidades y configuración
│   └── styles/              # Estilos globales
├── public/                  # Recursos estáticos
├── .env.example             # Variables de entorno de ejemplo
├── next.config.ts
├── package.json
└── README.md
```

## Configuración prevista

| Variable | Obligatoria | Descripción |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Sí | URL base del backend, por ejemplo `http://127.0.0.1:8000`. |

Ejemplo de `.env.local` (no versionar):

```bash
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

## Comandos previstos

Estos comandos estarán disponibles una vez creada la aplicación:

```bash
npm install
npm run dev       # http://localhost:3000
npm run build
npm run start
npm run lint
```

## Integración con el backend

### Autenticación

1. El usuario se registra en `POST /api/v1/auth/register/` o inicia sesión en `POST /api/v1/auth/login/`.
2. El backend devuelve `{token, user}`.
3. El frontend debe almacenar el token de forma segura y enviarlo en las peticiones protegidas:

```http
Authorization: Token <token>
```

4. `POST /api/v1/auth/logout/` invalida el token actual.
5. `GET/PATCH /api/v1/auth/me/` permite consultar y actualizar el perfil.

> No usar `localStorage` para tokens en producción si se puede evitar; evaluar cookies `HttpOnly` con un proxy/BFF en Next.js. La decisión debe tomarse antes de implementar el login.

### Módulos de la API

| Módulo | Prefijo | Uso en el frontend |
|---|---|---|
| Catálogo | `/api/v1/catalogo/` | Listado, filtros y detalle de videojuegos. |
| Carrito | `/api/v1/pedidos/carrito/` | Agregar, actualizar y quitar ítems. |
| Pedidos | `/api/v1/pedidos/` | Historial, detalle y cancelación. |
| Pagos | `/api/v1/pagos/` | Checkout y pago simulado. |
| Reportes | `/api/v1/reportes/` | Dashboard administrativo (solo staff). |
| Soporte | `/api/v1/soporte/` | Contacto y solicitud de información. |

El contrato detallado, filtros, permisos y ejemplos están en [`../backend/README.md`](../backend/README.md).

### Reglas importantes

- **El pago es simulado.** La UI debe comunicarlo explícitamente y no solicitar datos de tarjeta.
- **No duplicar reglas de negocio.** El stock, los totales, la cancelación y los permisos se validan en el backend.
- **Staff:** las pantallas de reportes y la bandeja de contactos deben verificar `user.is_staff`.
- **Paginación:** las listas devuelven `{count, next, previous, results}`.
- **Medios:** las portadas y fotos son URLs absolutas si se configuró S3; en desarrollo apuntan a `/media/`.
- **CORS:** el backend ya permite `http://localhost:3000` y `http://127.0.0.1:3000`. En producción se configura `CORS_ALLOWED_ORIGINS`.

## Flujo de desarrollo propuesto

```text
Django backend  →  http://127.0.0.1:8000
Next.js frontend →  http://localhost:3000
```

El frontend consumirá la API; no compartirá base de datos ni lógica de negocio.

## Convenciones

- TypeScript estricto.
- Componentes de servidor por defecto; componentes de cliente solo cuando sea necesario.
- No incluir secretos en variables `NEXT_PUBLIC_*`; esas variables son visibles en el navegador.
- Mantener los tipos del contrato de API en `src/lib` o generarlos desde el backend.
- No duplicar reglas de negocio del backend en el frontend.

## Próximo paso

Crear la aplicación Next.js en un issue independiente, definir el diseño de UI y consumir los endpoints existentes. El backend ya no contiene ninguna interfaz que reemplazar.

## Documentación relacionada

- [README principal](../README.md)
- [API del backend](../backend/README.md)
- [Plan del Sprint 1](../docs/sprints/SPRINT-1.md)
