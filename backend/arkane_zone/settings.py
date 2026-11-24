from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "backend"])

# Render expone el hostname del servicio en esta variable; lo agregamos automáticamente.
RENDER_EXTERNAL_HOSTNAME = env("RENDER_EXTERNAL_HOSTNAME", default=None)
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

INSTALLED_APPS = [
    # django-unfold debe ir antes de django.contrib.admin
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # API REST
    "corsheaders",
    "rest_framework",
    "rest_framework.authtoken",
    "api",
    # Apps del proyecto
    "cuentas",
    "catalogo",
    "inventario",
    "pedidos",
    "pagos",
    "reportes",
    "soporte",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # debe ir justo después de SecurityMiddleware
    # CORS debe ejecutarse antes de CommonMiddleware.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Garantiza respuestas JSON ante errores no controlados dentro de /api/.
    "api.middleware.ApiErrorMiddleware",
]

ROOT_URLCONF = "arkane_zone.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            "builtins": [
                "catalogo.templatetags.arkane_filters",
            ],
        },
    },
]

WSGI_APPLICATION = "arkane_zone.wsgi.application"

_database_url = env("DATABASE_URL", default="")
if _database_url:
    _db_config = env.db_url_config(_database_url)
else:
    # En Docker Compose la configuración se pasa como variables POSTGRES_*.
    # Así se evita tener que URL-encodear contraseñas dentro de DATABASE_URL.
    _db_config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST", default="db"),
        "PORT": env("POSTGRES_PORT", default="5432"),
    }
_db_config["CONN_MAX_AGE"] = 0
DATABASES = {"default": _db_config}

AUTH_USER_MODEL = "cuentas.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise: sirve estáticos comprimidos y con caché en producción.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ── Almacenamiento de medios ──────────────────────────────────────────────────
# Si AWS_ACCESS_KEY_ID está definida en .env → Supabase Storage (S3).
# Si no está → disco local (comportamiento por defecto de Django).
_USE_S3 = bool(env("AWS_ACCESS_KEY_ID", default=""))

if _USE_S3:
    AWS_ACCESS_KEY_ID      = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY  = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="media")
    AWS_S3_ENDPOINT_URL    = env("AWS_S3_ENDPOINT_URL")
    AWS_S3_REGION_NAME     = env("AWS_S3_REGION_NAME", default="us-west-2")
    # Dominio público del bucket, sin protocolo. Formato esperado:
    #   <project-ref>.supabase.co/storage/v1/object/public/media
    AWS_S3_CUSTOM_DOMAIN   = env("AWS_S3_CUSTOM_DOMAIN")
    AWS_QUERYSTRING_AUTH   = False   # bucket público → URLs sin firma
    AWS_DEFAULT_ACL        = "public-read"
    AWS_S3_FILE_OVERWRITE  = False   # evita sobreescribir archivos con mismo nombre

    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
    }
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/cuentas/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/cuentas/login/"

# ── Correo y recuperación de contraseña ───────────────────────────────────────
# En desarrollo se mantiene el backend de consola: el enlace se imprime en la
# terminal. Si se define EMAIL_HOST se pasa a SMTP salvo override explícito.
def configuracion_correo_desde_entorno() -> dict:
    """Resuelve SMTP, validez del token y URL del enlace del correo."""
    host = env("EMAIL_HOST", default="")
    backend_defecto = (
        "django.core.mail.backends.smtp.EmailBackend"
        if host
        else "django.core.mail.backends.console.EmailBackend"
    )
    return {
        "EMAIL_BACKEND": env("EMAIL_BACKEND", default=backend_defecto),
        "EMAIL_HOST": host,
        "EMAIL_PORT": env.int("EMAIL_PORT", default=25),
        "EMAIL_HOST_USER": env("EMAIL_HOST_USER", default=""),
        "EMAIL_HOST_PASSWORD": env("EMAIL_HOST_PASSWORD", default=""),
        "EMAIL_USE_TLS": env.bool("EMAIL_USE_TLS", default=False),
        "EMAIL_USE_SSL": env.bool("EMAIL_USE_SSL", default=False),
        "EMAIL_TIMEOUT": env.int("EMAIL_TIMEOUT", default=10),
        "DEFAULT_FROM_EMAIL": env(
            "DEFAULT_FROM_EMAIL", default="Arcakane Zone <noreply@arkanezone.co>"
        ),
        "PASSWORD_RESET_TIMEOUT": max(1, env.int("PASSWORD_RESET_TIMEOUT", default=3600)),
        "FRONTEND_BASE_URL": env(
            "FRONTEND_BASE_URL", default="http://localhost:5173"
        ).rstrip("/"),
        "PASSWORD_RESET_FRONTEND_PATH": env(
            "PASSWORD_RESET_FRONTEND_PATH",
            default="/restablecer-contrasena/{uid}/{token}",
        ),
        "PASSWORD_RESET_MAX_EMAILS_PER_HOUR": max(
            1, env.int("PASSWORD_RESET_MAX_EMAILS_PER_HOUR", default=3)
        ),
    }


_correo = configuracion_correo_desde_entorno()
EMAIL_BACKEND = _correo["EMAIL_BACKEND"]
EMAIL_HOST = _correo["EMAIL_HOST"]
EMAIL_PORT = _correo["EMAIL_PORT"]
EMAIL_HOST_USER = _correo["EMAIL_HOST_USER"]
EMAIL_HOST_PASSWORD = _correo["EMAIL_HOST_PASSWORD"]
EMAIL_USE_TLS = _correo["EMAIL_USE_TLS"]
EMAIL_USE_SSL = _correo["EMAIL_USE_SSL"]
EMAIL_TIMEOUT = _correo["EMAIL_TIMEOUT"]
DEFAULT_FROM_EMAIL = _correo["DEFAULT_FROM_EMAIL"]
PASSWORD_RESET_TIMEOUT = _correo["PASSWORD_RESET_TIMEOUT"]
FRONTEND_BASE_URL = _correo["FRONTEND_BASE_URL"]
PASSWORD_RESET_FRONTEND_PATH = _correo["PASSWORD_RESET_FRONTEND_PATH"]
PASSWORD_RESET_MAX_EMAILS_PER_HOUR = _correo["PASSWORD_RESET_MAX_EMAILS_PER_HOUR"]

# CSRF: permite peticiones desde el dominio de Render en producción.
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
)
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# ── Caché compartida y protección contra fuerza bruta ────────────────────────
# Por defecto los contadores de throttling viven en una tabla de PostgreSQL,
# creada por `manage.py createcachetable` (no requiere migraciones). Con
# REDIS_URL se usa Redis; el paquete `redis` debe estar instalado en el entorno.
def tasa_desde_entorno(nombre: str, defecto: str) -> str | None:
    """Lee una tasa DRF; una cadena vacía desactiva el scope indicado."""
    valor = env(f"THROTTLE_RATE_{nombre}", default=defecto)
    return str(valor).strip() or None


CACHE_TABLE = env("CACHE_TABLE", default="django_cache")
REDIS_URL = env("REDIS_URL", default=None)
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.db.DatabaseCache",
            "LOCATION": CACHE_TABLE,
        }
    }

# 0 = confiar solo en REMOTE_ADDR; > 0 = leer X-Forwarded-For desde la derecha.
THROTTLE_NUM_PROXIES = max(0, env.int("THROTTLE_NUM_PROXIES", default=0))
LOGIN_MAX_FAILED_ATTEMPTS = max(1, env.int("LOGIN_MAX_FAILED_ATTEMPTS", default=5))
LOGIN_FAILURE_WINDOW_SECONDS = max(1, env.int("LOGIN_FAILURE_WINDOW_SECONDS", default=900))
LOGIN_LOCKOUT_SECONDS = max(1, env.int("LOGIN_LOCKOUT_SECONDS", default=900))

# ── API REST ─────────────────────────────────────────────────────────────────
# Autenticación por token (clientes desacoplados) y por sesión/cookie
# (misma sesión que usa el sitio y el admin de Django).
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Por defecto todo exige autenticación; cada vista pública lo declara.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "api.renderers.EnvelopeJSONRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "api.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "api.exceptions.api_exception_handler",
    # Throttling: globales anon/user + scopes específicos de las rutas sensibles.
    "DEFAULT_THROTTLE_CLASSES": [
        "api.throttling.AnonimoRateThrottle",
        "api.throttling.UsuarioRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": tasa_desde_entorno("ANON", "100/min"),
        "user": tasa_desde_entorno("USER", "1000/hour"),
        "login": tasa_desde_entorno("LOGIN", "10/min"),
        "registro": tasa_desde_entorno("REGISTRO", "5/hour"),
        "contacto": tasa_desde_entorno("CONTACTO", "5/hour"),
        "password_reset": tasa_desde_entorno("PASSWORD_RESET", "5/hour"),
    },
    "NUM_PROXIES": THROTTLE_NUM_PROXIES,
    # Respuestas JSON legibles (tildes y eñes sin escapes).
    "UNICODE_JSON": True,
    "COMPACT_JSON": False,
    # Los importes viajan como cadenas decimales para no perder precisión.
    "COERCE_DECIMAL_TO_STRING": True,
}

# CORS: el frontend puede vivir en otro origen (por ejemplo, un dominio
# distinto en Render). Con el proxy /api de Vite/Nginx no hace falta, pero
# se deja configurable para integraciones directas.
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
)
CORS_ALLOW_CREDENTIALS = True

# Detrás de un proxy inverso (Nginx, Render, etc.) que termina TLS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=False)

# Seguridad adicional en producción (no aplica en local con DEBUG=True).
# En Docker el healthcheck interno viaja por HTTP, por eso SECURE_SSL_REDIRECT
# se puede desactivar dentro del contenedor cuando TLS termina en el proxy.
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# django-unfold — paleta azul eléctrico (valores en RGB sin #)
UNFOLD = {
    "SITE_TITLE": "Arcakane Zone",
    "SITE_HEADER": "Arcakane Zone Admin",
    "SITE_URL": "/",
    "COLORS": {
        "primary": {
            "50":  "224 242 254",
            "100": "186 230 253",
            "200": "125 211 252",
            "300": "56  189 248",
            "400": "14  165 233",
            "500": "2   132 199",   # acento principal admin (#0284C7)
            "600": "3   105 161",
            "700": "7   89  133",
            "800": "12  74  110",
            "900": "8   47  73",
            "950": "5   25  50",
        },
    },
}
