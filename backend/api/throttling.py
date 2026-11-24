"""Throttling de la API y bloqueo temporal de login por fuerza bruta.

Las tasas se leen en cada petición (no se congelan al importar) para que
``override_settings`` funcione en las pruebas y los cambios de entorno no
requieran reiniciar el proceso.
"""
import hashlib
import math
import time

from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import Throttled
from rest_framework.settings import api_settings
from rest_framework.throttling import BaseThrottle, SimpleRateThrottle

class BloqueoLogin(Throttled):
    """429 de bloqueo por fuerza bruta; no revela si el usuario existe."""

    default_detail = (
        "Demasiados intentos fallidos de inicio de sesión. "
        "Intenta de nuevo en unos minutos."
    )
    default_code = "demasiadas_solicitudes"


_PREFIJO_CONTADOR = "az:login:fallos:"
_PREFIJO_BLOQUEO = "az:login:bloqueo:"


class TasaConfigurableMixin:
    """Resuelve ``DEFAULT_THROTTLE_RATES`` en cada petición."""

    def get_rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES.get(self.scope)


class ScopeFijoRateThrottle(TasaConfigurableMixin, SimpleRateThrottle):
    """Scope fijo por clase, sin depender de ``view.throttle_scope``."""

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class AnonimoRateThrottle(ScopeFijoRateThrottle):
    """Scope global ``anon``: solo visitantes."""

    scope = "anon"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None
        return super().get_cache_key(request, view)


class UsuarioRateThrottle(ScopeFijoRateThrottle):
    """Scope global ``user``: solo usuarios autenticados."""

    scope = "user"

    def get_cache_key(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return None
        return super().get_cache_key(request, view)


class LoginRateThrottle(ScopeFijoRateThrottle):
    scope = "login"


class RegistroRateThrottle(ScopeFijoRateThrottle):
    scope = "registro"


class ContactoRateThrottle(ScopeFijoRateThrottle):
    scope = "contacto"


def ip_del_cliente(request):
    """IP efectiva: ``REMOTE_ADDR`` salvo proxies de confianza explícitos."""
    cabecera = request.META.get("HTTP_X_FORWARDED_FOR")
    remota = request.META.get("REMOTE_ADDR")
    num_proxies = max(0, int(getattr(settings, "THROTTLE_NUM_PROXIES", 0) or 0))
    if num_proxies == 0 or cabecera is None:
        return remota or "unknown"
    direcciones = [d.strip() for d in cabecera.split(",") if d.strip()]
    if not direcciones:
        return remota or "unknown"
    return direcciones[-min(num_proxies, len(direcciones))]


class PasswordResetRateThrottle(ScopeFijoRateThrottle):
    """Scope ``password_reset``: siempre por IP, incluso con sesión activa."""

    scope = "password_reset"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": ip_del_cliente(request),
        }


def _hash_login(request, username):
    """Hash de usuario normalizado + IP; nunca guarda la contraseña."""
    usuario = str(username or "").strip().lower()
    origen = f"{usuario}|{ip_del_cliente(request)}".encode("utf-8")
    return hashlib.sha256(origen).hexdigest()


def segundos_de_bloqueo(request, username):
    """Segundos restantes de bloqueo, o ``0`` si la clave no está bloqueada."""
    clave = _PREFIJO_BLOQUEO + _hash_login(request, username)
    expira = cache.get(clave)
    if expira is None:
        return 0
    try:
        restante = math.ceil(float(expira) - time.time())
    except (TypeError, ValueError):
        cache.delete(clave)
        return 0
    if restante <= 0:
        cache.delete(clave)
        return 0
    return restante


def registrar_intento_fallido(request, username):
    """Cuenta un ``401`` y bloquea al alcanzar ``LOGIN_MAX_FAILED_ATTEMPTS``."""
    digest = _hash_login(request, username)
    clave_contador = _PREFIJO_CONTADOR + digest
    clave_bloqueo = _PREFIJO_BLOQUEO + digest
    ahora = time.time()
    max_intentos = max(1, int(getattr(settings, "LOGIN_MAX_FAILED_ATTEMPTS", 5)))
    ventana = max(1, int(getattr(settings, "LOGIN_FAILURE_WINDOW_SECONDS", 900)))

    registro = cache.get(clave_contador)
    if not isinstance(registro, dict):
        registro = {"intentos": 0, "expira": ahora + ventana}
    else:
        try:
            expira = float(registro.get("expira", 0))
        except (TypeError, ValueError):
            expira = 0
        if expira <= ahora:
            registro = {"intentos": 0, "expira": ahora + ventana}

    registro["intentos"] = int(registro.get("intentos", 0)) + 1
    cache.set(
        clave_contador,
        registro,
        timeout=max(1, math.ceil(registro["expira"] - ahora)),
    )
    if registro["intentos"] >= max_intentos:
        bloqueo = max(1, int(getattr(settings, "LOGIN_LOCKOUT_SECONDS", 900)))
        cache.set(clave_bloqueo, ahora + bloqueo, timeout=bloqueo)
        cache.delete(clave_contador)


def reiniciar_intentos_login(request, username):
    """Borra contador y bloqueo tras un inicio de sesión correcto."""
    digest = _hash_login(request, username)
    cache.delete_many([_PREFIJO_CONTADOR + digest, _PREFIJO_BLOQUEO + digest])


class BloqueoLoginThrottle(BaseThrottle):
    """Se ejecuta antes de la autenticación; no comprueba la contraseña."""

    def allow_request(self, request, view):
        datos = getattr(request, "data", None) or {}
        username = datos.get("username", "") if hasattr(datos, "get") else ""
        if not username:
            return True
        restante = segundos_de_bloqueo(request, username)
        if restante:
            raise BloqueoLogin(wait=restante)
        return True
