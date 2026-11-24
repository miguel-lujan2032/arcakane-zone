"""Manejo centralizado de errores y respuestas exitosas de la API."""
import logging
import math
from typing import Any

from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .throttling import BloqueoLogin

logger = logging.getLogger(__name__)


class ErrorDeNegocio(APIException):
    """Error de regla de negocio que se traduce a ``409 Conflict``."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "La operación no se pudo completar por una regla de negocio."
    default_code = "conflicto"

    def __init__(self, detail: str | None = None, extra: dict | None = None):
        super().__init__(detail or self.default_detail)
        self.extra = extra or {}


def respuesta_exitosa(
    data: Any = None,
    message: str | None = None,
    status_code: int = status.HTTP_200_OK,
    **extra,
) -> Response:
    """Construye una respuesta exitosa con el sobre JSON estándar."""
    payload = {"success": True, "data": data}
    if message:
        payload["message"] = message
    payload.update(extra)
    return Response(payload, status=status_code)


def respuesta_error(
    codigo: str,
    mensaje: str,
    detalles: Any = None,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    """Construye una respuesta de error con el sobre JSON estándar."""
    error = {"code": codigo, "message": mensaje}
    if detalles is not None:
        error["details"] = detalles
    return Response({"success": False, "error": error}, status=status_code)


def _normalizar_detalles(valor):
    """Convierte ``ErrorDetail`` y estructuras anidadas en tipos JSON simples."""
    if isinstance(valor, dict):
        return {str(clave): _normalizar_detalles(contenido) for clave, contenido in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_normalizar_detalles(item) for item in valor]
    return str(valor)


def _codigo_y_mensaje(exc) -> tuple[str, str]:
    if isinstance(exc, ValidationError):
        return "datos_invalidos", "Datos de entrada inválidos."
    if isinstance(exc, NotAuthenticated):
        return "no_autenticado", "Se requiere autenticación para realizar esta operación."
    if isinstance(exc, AuthenticationFailed):
        return "credenciales_invalidas", "Usuario o contraseña incorrectos."
    if isinstance(exc, PermissionDenied):
        return "permiso_denegado", "No tienes permiso para realizar esta operación."
    if isinstance(exc, NotFound):
        return "no_encontrado", "El recurso solicitado no existe."
    if isinstance(exc, MethodNotAllowed):
        return "metodo_no_permitido", "El método HTTP no está permitido para este recurso."
    if isinstance(exc, BloqueoLogin):
        return "demasiadas_solicitudes", str(exc.detail)
    if isinstance(exc, Throttled):
        return "demasiadas_solicitudes", "Se superó el límite de solicitudes. Intenta más tarde."
    if isinstance(exc, ErrorDeNegocio):
        return exc.default_code, str(exc.detail)
    if isinstance(exc, APIException):
        return getattr(exc, "default_code", "error_api"), str(exc.detail)
    return "error_api", "No se pudo completar la solicitud."


def api_exception_handler(exc, context):
    """Convierte cualquier excepción en el sobre de error JSON de la API."""
    if isinstance(exc, ProtectedError):
        return respuesta_error(
            "conflicto",
            "No se puede eliminar el recurso porque está referenciado por otros registros.",
            status_code=status.HTTP_409_CONFLICT,
        )
    if isinstance(exc, IntegrityError):
        logger.warning("Conflicto de integridad en la API: %s", exc)
        return respuesta_error(
            "conflicto",
            "La operación viola una restricción de integridad de los datos.",
            status_code=status.HTTP_409_CONFLICT,
        )

    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Error no controlado en la API", exc_info=exc)
        return respuesta_error(
            "error_interno",
            "Ocurrió un error interno al procesar la solicitud.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    codigo, mensaje = _codigo_y_mensaje(exc)
    detalles = getattr(exc, "extra", None)
    if not detalles:
        if isinstance(exc, ValidationError):
            detalles = _normalizar_detalles(response.data)
        else:
            data = response.data
            if isinstance(data, dict) and set(data.keys()) == {"detail"}:
                detalles = None
            else:
                detalles = _normalizar_detalles(data)

    payload = {"success": False, "error": {"code": codigo, "message": mensaje}}
    if detalles:
        payload["error"]["details"] = detalles
    response.data = payload
    if isinstance(exc, Throttled) and getattr(exc, "wait", None) is not None:
        # DRF ya lo hace, pero lo reforzamos para no perderlo al reemplazar data.
        response["Retry-After"] = str(max(1, math.ceil(exc.wait)))
    return response
