# Configuración exclusiva para la suite de pruebas automatizadas.
# Usa SQLite en memoria → jamás toca la base de datos de producción.
import os

# Valores seguros para tests: se definen antes de importar settings para que
# un clon limpio pueda ejecutar pytest sin un archivo .env.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "True")

from .settings import *  # noqa: F401, F403, E402

DEBUG = True
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Hasheo rápido: hace que los tests sean más veloces.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Desactiva el backend real de correo durante tests.
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
