from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

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
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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

_db_config = env.db("DATABASE_URL")
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
STATICFILES_DIRS = [BASE_DIR / "static"]
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

# Correo: backend de consola para desarrollo (imprime el enlace de reseteo en la terminal).
# En producción cambiar por smtp.EmailBackend y configurar SMTP.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "Arkane Zone <noreply@arkanezone.co>"

# CSRF: permite peticiones desde el dominio de Render en producción.
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:8000", "http://127.0.0.1:8000"],
)
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# Seguridad adicional en producción (no aplica en local con DEBUG=True)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# django-unfold — paleta azul eléctrico (valores en RGB sin #)
UNFOLD = {
    "SITE_TITLE": "Arkane Zone",
    "SITE_HEADER": "Arkane Zone Admin",
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
