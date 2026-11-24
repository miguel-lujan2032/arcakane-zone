"""Pruebas de throttling, bloqueo de login y respuestas 429."""
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework.views import APIView

from api.throttling import AnonimoRateThrottle, UsuarioRateThrottle
from arkane_zone import settings as django_settings

pytestmark = pytest.mark.django_db

LOGIN_URL = "/api/v1/auth/login/"
REGISTRO_URL = "/api/v1/auth/registro/"
CONTACTO_URL = "/api/v1/soporte/contactos/"
INFO_URL = "/api/v1/soporte/mayor-informacion/"
HEALTH_URL = "/api/v1/health/"
PASSWORD = "ClaveSegura#2026"


def _cliente(ip="127.0.0.1"):
    cliente = APIClient()
    cliente.defaults["REMOTE_ADDR"] = ip
    return cliente


def _login(cliente, username, password):
    return cliente.post(
        LOGIN_URL, {"username": username, "password": password}, format="json"
    )


def _registro(cliente, username, email):
    return cliente.post(
        REGISTRO_URL,
        {
            "username": username,
            "email": email,
            "password": PASSWORD,
            "password_confirm": PASSWORD,
        },
        format="json",
    )


def _contacto(cliente, email):
    return cliente.post(
        CONTACTO_URL,
        {
            "nombre": "Visitante",
            "email": email,
            "asunto": "Consulta",
            "mensaje": "Necesito información.",
        },
        format="json",
    )


def _assert_429(respuesta, fragmento=None):
    assert respuesta.status_code == 429
    payload = respuesta.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "demasiadas_solicitudes"
    assert int(respuesta["Retry-After"]) >= 1
    if fragmento:
        assert fragmento in payload["error"]["message"]


def _rates(**por_scope):
    """Copia REST_FRAMEWORK con todos los scopes desactivados salvo los dados."""
    configuracion = dict(settings.REST_FRAMEWORK)
    tasas = {scope: None for scope in configuracion["DEFAULT_THROTTLE_RATES"]}
    tasas.update(por_scope)
    configuracion["DEFAULT_THROTTLE_RATES"] = tasas
    return configuracion


@override_settings(
    LOGIN_MAX_FAILED_ATTEMPTS=2,
    LOGIN_FAILURE_WINDOW_SECONDS=900,
    LOGIN_LOCKOUT_SECONDS=900,
)
def test_login_bloquea_en_el_intento_n_mas_uno(usuario_cliente):
    cliente = _cliente()

    assert _login(cliente, usuario_cliente.username, "incorrecta").status_code == 401
    assert _login(cliente, usuario_cliente.username, "incorrecta").status_code == 401

    with patch("api.views.auth.authenticate") as autenticar:
        respuesta = _login(cliente, usuario_cliente.username, "pass1234!")

    autenticar.assert_not_called()
    _assert_429(respuesta, "intentos fallidos")


@override_settings(
    LOGIN_MAX_FAILED_ATTEMPTS=3,
    LOGIN_FAILURE_WINDOW_SECONDS=900,
    LOGIN_LOCKOUT_SECONDS=900,
)
def test_login_correcto_reinicia_el_contador(usuario_cliente):
    cliente = _cliente()
    username = usuario_cliente.username

    assert _login(cliente, username, "incorrecta").status_code == 401
    assert _login(cliente, username, "incorrecta").status_code == 401
    assert _login(cliente, username, "pass1234!").status_code == 200

    assert _login(cliente, username, "incorrecta").status_code == 401
    assert _login(cliente, username, "incorrecta").status_code == 401
    assert _login(cliente, username, "pass1234!").status_code == 200


@override_settings(
    LOGIN_MAX_FAILED_ATTEMPTS=1,
    LOGIN_FAILURE_WINDOW_SECONDS=900,
    LOGIN_LOCKOUT_SECONDS=900,
)
def test_bloqueo_es_por_usuario_y_ip(usuario_cliente, usuario_admin):
    cliente = _cliente("1.1.1.1")

    assert _login(cliente, usuario_cliente.username, "incorrecta").status_code == 401
    _assert_429(_login(cliente, usuario_cliente.username, "pass1234!"))

    otro_ip = _cliente("2.2.2.2")
    assert _login(otro_ip, usuario_cliente.username, "pass1234!").status_code == 200
    assert _login(cliente, usuario_admin.username, "pass1234!").status_code == 200


@override_settings(
    LOGIN_MAX_FAILED_ATTEMPTS=1,
    LOGIN_FAILURE_WINDOW_SECONDS=900,
    LOGIN_LOCKOUT_SECONDS=60,
)
def test_bloqueo_expira_con_tiempo_simulado(usuario_cliente):
    cliente = _cliente()

    with patch("api.throttling.time.time", return_value=1000.0):
        assert _login(cliente, usuario_cliente.username, "incorrecta").status_code == 401
        _assert_429(_login(cliente, usuario_cliente.username, "pass1234!"))

    with patch("api.throttling.time.time", return_value=1061.0):
        assert _login(cliente, usuario_cliente.username, "pass1234!").status_code == 200


@override_settings(LOGIN_MAX_FAILED_ATTEMPTS=1)
def test_errores_de_validacion_no_cuentan_como_fallos(usuario_cliente):
    cliente = _cliente()

    for _ in range(3):
        respuesta = cliente.post(
            LOGIN_URL, {"username": usuario_cliente.username}, format="json"
        )
        assert respuesta.status_code == 400

    assert _login(cliente, usuario_cliente.username, "pass1234!").status_code == 200


def test_limite_de_registro_devuelve_429_con_retry_after():
    with override_settings(REST_FRAMEWORK=_rates(registro="2/min")):
        # Cliente nuevo por petición: registro inicia sesión y cambiaría la clave.
        assert _registro(_cliente(), "uno", "uno@test.com").status_code == 201
        assert _registro(_cliente(), "dos", "dos@test.com").status_code == 201
        respuesta = _registro(_cliente(), "tres", "tres@test.com")
        _assert_429(respuesta, "límite de solicitudes")


def test_limite_de_contacto_devuelve_429_con_retry_after():
    with override_settings(REST_FRAMEWORK=_rates(contacto="2/min")):
        cliente = _cliente()

        assert _contacto(cliente, "uno@test.com").status_code == 201
        assert _contacto(cliente, "dos@test.com").status_code == 201
        _assert_429(_contacto(cliente, "tres@test.com"), "límite de solicitudes")

        respuesta = cliente.post(
            INFO_URL,
            {"nombre": "Interesado", "email": "cuatro@test.com"},
            format="json",
        )
        _assert_429(respuesta, "límite de solicitudes")


def test_limite_global_anon():
    configuracion = _rates(anon="2/min")

    # DRF evalúa APIView.throttle_classes al importar; se parchea explícitamente.
    with override_settings(REST_FRAMEWORK=configuracion), patch.object(
        APIView, "throttle_classes", [AnonimoRateThrottle]
    ):
        cliente = _cliente()
        assert cliente.get(HEALTH_URL).status_code == 200
        assert cliente.get(HEALTH_URL).status_code == 200
        _assert_429(cliente.get(HEALTH_URL), "límite de solicitudes")


def test_limite_global_user(usuario_cliente):
    configuracion = _rates(user="2/min")

    with override_settings(REST_FRAMEWORK=configuracion), patch.object(
        APIView, "throttle_classes", [UsuarioRateThrottle]
    ):
        cliente = APIClient()
        cliente.force_authenticate(usuario_cliente)
        assert cliente.get(HEALTH_URL).status_code == 200
        assert cliente.get(HEALTH_URL).status_code == 200
        _assert_429(cliente.get(HEALTH_URL), "límite de solicitudes")


def test_las_tasas_se_leen_de_variables_de_entorno(monkeypatch):
    monkeypatch.setenv("THROTTLE_RATE_LOGIN", "7/min")
    assert django_settings.tasa_desde_entorno("LOGIN", "10/min") == "7/min"

    monkeypatch.setenv("THROTTLE_RATE_LOGIN", "   ")
    assert django_settings.tasa_desde_entorno("LOGIN", "10/min") is None


def test_la_cache_se_llena_dentro_de_una_prueba():
    cache.set("prueba_aislamiento", "valor", 60)
    assert cache.get("prueba_aislamiento") == "valor"


def test_la_cache_no_se_contamina_entre_pruebas():
    assert cache.get("prueba_aislamiento") is None
