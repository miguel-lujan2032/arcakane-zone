# Arkane Zone — Frontend (Next.js)

Aplicación de interfaz de usuario para Arkane Zone. **Esta carpeta es un placeholder:** el frontend todavía no está implementado. La aplicación actual sigue siendo servida por Django Templates + HTMX desde [`../backend/`](../backend/README.md).

El objetivo es construir aquí una aplicación independiente con **Next.js** que consuma una API JSON del backend.

## Estado

| Elemento | Estado |
|---|---|
| Aplicación Next.js | No creada |
| Contrato de API | No definido |
| Autenticación | Por definir (sesión/cookies o tokens) |
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

Antes de implementar pantallas hay que resolver estas decisiones con el equipo:

1. **Contrato de API:** el backend actual devuelve HTML, no JSON. Se deben definir endpoints para catálogo, carrito, pedidos, pagos, reportes y soporte.
2. **Autenticación:** elegir entre sesión con cookies (CSRF/CORS) o tokens. La decisión afecta el manejo de login, logout y rutas protegidas.
3. **CORS y CSRF:** configurar `CORS_ALLOWED_ORIGINS`/`CSRF_TRUSTED_ORIGINS` en Django para el origen de Next.js.
4. **Pagos:** el pago es simulado; la UI debe comunicarlo explícitamente y no solicitar datos de tarjeta.
5. **Medios:** las portadas y fotos requieren una estrategia de almacenamiento (S3/Supabase Storage) para producción.
6. **Reportes:** son de uso administrativo; definir si se implementan en Next.js o se mantienen en el admin de Django.

## Flujo de desarrollo propuesto

```text
Django backend  →  http://127.0.0.1:8000
Next.js frontend →  http://localhost:3000
```

El frontend consumirá la API del backend; no compartirá base de datos ni lógica de negocio.

## Convenciones

- TypeScript estricto.
- Componentes de servidor por defecto; componentes de cliente solo cuando sea necesario.
- No incluir secretos en variables `NEXT_PUBLIC_*`; esas variables son visibles en el navegador.
- Mantener los tipos del contrato de API en `src/lib` o generarlos desde el backend.
- No duplicar reglas de negocio del backend en el frontend.

## Próximo paso

Crear la aplicación Next.js en un issue independiente, definir el contrato de API con el equipo y reemplazar progresivamente la interfaz Django. Mientras tanto, el backend sigue siendo la aplicación funcional.

## Documentación relacionada

- [README principal](../README.md)
- [Backend Django](../backend/README.md)
- [Plan del Sprint 1](../docs/sprints/SPRINT-1.md)
