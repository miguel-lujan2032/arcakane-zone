"""Lógica aislada de recuperación de contraseña por API.

El token y el uid usan el generador estándar de Django: el token cambia al
cambiar la contraseña (un solo uso) y vence según ``PASSWORD_RESET_TIMEOUT``.
Aquí no se registran tokens ni correos en logs.
"""
import hashlib
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import APIException


class TokenResetInvalido(APIException):
    """uid/token ausente, manipulado o vencido: siempre el mismo error."""

    status_code = 400
    default_detail = "El enlace de restablecimiento no es válido o venció."
    default_code = "token_invalido"


_PREFIJO_ENVIO = "az:password_reset:email:"
_VENTANA_ENVIO_SEGUNDOS = 3600


def normalizar_email(email) -> str:
    return str(email or "").strip().lower()


def registrar_envio_correo(email) -> bool:
    """Cuenta un envío por hora y dice si cabe en el tope por correo."""
    correo = normalizar_email(email)
    clave = _PREFIJO_ENVIO + hashlib.sha256(correo.encode("utf-8")).hexdigest()
    ahora = time.time()
    limite = max(
        1, int(getattr(settings, "PASSWORD_RESET_MAX_EMAILS_PER_HOUR", 3))
    )
    registro = cache.get(clave)
    if not isinstance(registro, dict):
        registro = {"enviados": 0, "expira": ahora + _VENTANA_ENVIO_SEGUNDOS}
    else:
        try:
            expira = float(registro.get("expira", 0))
        except (TypeError, ValueError):
            expira = 0
        if expira <= ahora:
            registro = {"enviados": 0, "expira": ahora + _VENTANA_ENVIO_SEGUNDOS}

    if int(registro.get("enviados", 0)) >= limite:
        return False
    registro["enviados"] = int(registro.get("enviados", 0)) + 1
    cache.set(clave, registro, timeout=max(1, int(registro["expira"] - ahora)))
    return True


def construir_enlace(uidb64: str, token: str) -> str:
    """Une la base del frontend con el patrón de ruta configurable."""
    base = str(getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173")).rstrip("/")
    patron = str(
        getattr(
            settings,
            "PASSWORD_RESET_FRONTEND_PATH",
            "/restablecer-contrasena/{uid}/{token}",
        )
    )
    if not patron.startswith("/"):
        patron = "/" + patron
    return base + patron.format(uid=uidb64, token=token)


def enviar_correo_reset(usuario):
    """Envía el correo en texto y HTML; devuelve ``(uid, token)``."""
    uidb64 = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = default_token_generator.make_token(usuario)
    contexto = {
        "enlace": construir_enlace(uidb64, token),
        "minutos": max(1, int(getattr(settings, "PASSWORD_RESET_TIMEOUT", 3600)) // 60),
    }
    mensaje = EmailMultiAlternatives(
        subject="Restablece tu contraseña en Arcakane Zone",
        body=render_to_string("emails/password_reset.txt", contexto),
        to=[usuario.email],
    )
    mensaje.attach_alternative(
        render_to_string("emails/password_reset.html", contexto), "text/html"
    )
    # Respuesta neutra incluso si el SMTP falla: no se filtra existencia.
    mensaje.send(fail_silently=True)
    return uidb64, token


def resolver_usuario(uidb64, token):
    """Devuelve el usuario si el enlace es válido; si no, error genérico."""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        usuario = get_user_model()._default_manager.get(pk=uid)
    except (
        TypeError,
        ValueError,
        OverflowError,
        UnicodeDecodeError,
        ValidationError,
        ObjectDoesNotExist,
    ) as exc:
        raise TokenResetInvalido() from exc

    if (
        not usuario.is_active
        or not usuario.has_usable_password()
        or not default_token_generator.check_token(usuario, token)
    ):
        raise TokenResetInvalido()
    return usuario
