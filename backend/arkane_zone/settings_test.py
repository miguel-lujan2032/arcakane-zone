# Configuración exclusiva para la suite de pruebas automatizadas.
# Usa SQLite en memoria → jamás toca la base de datos de Supabase.
import tempfile

from .settings import *  # noqa: F401, F403

# WhiteNoise exige que STATIC_ROOT exista; en tests evitamos depender de un
# ``collectstatic`` previo creando un directorio temporal.
STATIC_ROOT = tempfile.mkdtemp(prefix="arkane-zone-static-")

# La suite debe ser independiente de las variables del entorno: con DEBUG=False
# SECURE_SSL_REDIRECT redirigiría las peticiones HTTP de las pruebas (301).
DEBUG = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        # BEGIN IMMEDIATE en cada transacción: los escritores serializan
        # sobre el lock de la BD compartida en memoria (cache=shared), lo
        # que hace deterministas los tests de concurrencia con hilos del
        # libro mayor (AZ-S1-14). Sin esto, la escalada read→write de las
        # transacciones DEFERRED de SQLite produce "database is locked".
        "OPTIONS": {"transaction_mode": "IMMEDIATE"},
    }
}

# Hasheo rápido: hace que los tests sean 10x más veloces
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Desactiva el backend real de correo durante tests
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Throttling: caché aislada y límites altos por defecto. Cada prueba que
# necesita un límite concreto lo activa con `override_settings`.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "arkane-zone-tests",
    }
}
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        scope: None for scope in REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    },
}
THROTTLE_NUM_PROXIES = 0
LOGIN_MAX_FAILED_ATTEMPTS = 1_000_000
LOGIN_FAILURE_WINDOW_SECONDS = 900
LOGIN_LOCKOUT_SECONDS = 900

# Recuperación de contraseña: valores deterministas, sin depender del entorno.
PASSWORD_RESET_TIMEOUT = 3600
FRONTEND_BASE_URL = "http://localhost:5173"
PASSWORD_RESET_FRONTEND_PATH = "/restablecer-contrasena/{uid}/{token}"
PASSWORD_RESET_MAX_EMAILS_PER_HOUR = 3
