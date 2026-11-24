"""Pruebas de recuperación de contraseña por API."""
import re
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import Client, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from arkane_zone import settings as django_settings
from cuentas.models import Usuario

pytestmark = pytest.mark.django_db

SOLICITAR_URL = "/api/v1/auth/password-reset/"
CONFIRMAR_URL = "/api/v1/auth/password-reset/confirm/"
LOGIN_URL = "/api/v1/auth/login/"
ME_URL = "/api/v1/auth/me/"
PASSWORD_NUEVA = "NuevaClave#2026"


@pytest.fixture(autouse=True)
def aislar_correo_y_cache():
    mail.outbox.clear()
    cache.clear()


def _cliente(ip="127.0.0.1"):
    cliente = APIClient()
    cliente.defaults["REMOTE_ADDR"] = ip
    return cliente


def _solicitar(cliente, email):
    return cliente.post(SOLICITAR_URL, {"email": email}, format="json")


def _uid_token(mensaje):
    coincidencia = re.search(
        r"/restablecer-contrasena/([^/\s]+)/([^/\s]+)", mensaje.body
    )
    assert coincidencia
    return coincidencia.group(1), coincidencia.group(2)


def _datos_confirmar(uid, token, password=PASSWORD_NUEVA, confirmacion=None):
    return {
        "uid": uid,
        "token": token,
        "new_password": password,
        "new_password_confirm": confirmacion if confirmacion is not None else password,
    }


def _confirmar(cliente, datos):
    return cliente.post(CONFIRMAR_URL, datos, format="json")


def _rates(**por_scope):
    configuracion = dict(settings.REST_FRAMEWORK)
    tasas = {scope: None for scope in configuracion["DEFAULT_THROTTLE_RATES"]}
    tasas.update(por_scope)
    configuracion["DEFAULT_THROTTLE_RATES"] = tasas
    return configuracion


def test_flujo_completo_de_recuperacion(usuario_cliente):
    cliente = _cliente()
    assert _solicitar(cliente, usuario_cliente.email).status_code == 200
    assert len(mail.outbox) == 1

    uid, token = _uid_token(mail.outbox[0])
    respuesta = _confirmar(cliente, _datos_confirmar(uid, token))
    assert respuesta.status_code == 200
    assert respuesta.json()["success"] is True
    assert _cliente().post(
        LOGIN_URL,
        {"username": usuario_cliente.username, "password": PASSWORD_NUEVA},
        format="json",
    ).status_code == 200


def test_respuesta_neutra_para_cuenta_inexistente_inactiva_y_sin_password(usuario_cliente):
    cliente = _cliente()
    inactiva = Usuario.objects.create_user(
        username="inactiva", email="inactiva@test.com", password="pass1234!", is_active=False
    )
    sin_password = Usuario.objects.create_user(
        username="sinpassword", email="sinpassword@test.com"
    )
    sin_password.set_unusable_password()
    sin_password.save(update_fields=["password"])

    existente = _solicitar(cliente, usuario_cliente.email)
    inexistente = _solicitar(cliente, "nadie@test.com")
    inactiva_resp = _solicitar(cliente, inactiva.email)
    sin_password_resp = _solicitar(cliente, sin_password.email)

    assert existente.status_code == 200
    assert existente.json() == inexistente.json() == inactiva_resp.json()
    assert existente.json() == sin_password_resp.json()
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [usuario_cliente.email]


def test_envia_a_todas_las_cuentas_activas_con_mismo_email(usuario_cliente, usuario_admin):
    usuario_admin.email = usuario_cliente.email
    usuario_admin.save(update_fields=["email"])

    assert _solicitar(_cliente(), usuario_cliente.email).status_code == 200
    assert len(mail.outbox) == 2
    assert {mensaje.to[0] for mensaje in mail.outbox} == {usuario_cliente.email}


def test_correo_apunta_al_frontend_y_no_incluye_passwords(usuario_cliente):
    _solicitar(_cliente(), usuario_cliente.email)
    mensaje = mail.outbox[0]

    assert settings.FRONTEND_BASE_URL in mensaje.body
    assert "/restablecer-contrasena/" in mensaje.body
    assert "ignora este mensaje" in mensaje.body
    assert "minutos" in mensaje.body
    assert mensaje.subject
    assert mensaje.alternatives[0][1] == "text/html"
    assert "pass1234!" not in mensaje.body
    assert PASSWORD_NUEVA not in mensaje.body


def test_token_de_un_solo_uso(usuario_cliente):
    _solicitar(_cliente(), usuario_cliente.email)
    uid, token = _uid_token(mail.outbox[0])
    datos = _datos_confirmar(uid, token)

    assert _confirmar(_cliente(), datos).status_code == 200
    segunda = _confirmar(_cliente(), datos)
    assert segunda.status_code == 400
    assert segunda.json()["error"]["code"] == "token_invalido"


def test_token_vencido_da_400(usuario_cliente):
    _solicitar(_cliente(), usuario_cliente.email)
    uid, token = _uid_token(mail.outbox[0])
    futuro = datetime.now() + timedelta(seconds=7200)

    with override_settings(PASSWORD_RESET_TIMEOUT=60), patch.object(
        default_token_generator, "_now", return_value=futuro
    ):
        respuesta = _confirmar(_cliente(), _datos_confirmar(uid, token))

    assert respuesta.status_code == 400
    assert respuesta.json()["error"]["code"] == "token_invalido"


def test_uid_invalido_y_token_manipulado_dan_el_mismo_error(usuario_cliente):
    _solicitar(_cliente(), usuario_cliente.email)
    uid, token = _uid_token(mail.outbox[0])
    manipulado = token[:-1] + ("a" if token[-1] != "a" else "b")

    con_uid_invalido = _confirmar(
        _cliente(), _datos_confirmar("no-es-un-uid", token)
    )
    con_token_manipulado = _confirmar(_cliente(), _datos_confirmar(uid, manipulado))
    sin_token = _confirmar(_cliente(), _datos_confirmar(uid, ""))

    for respuesta in (con_uid_invalido, con_token_manipulado, sin_token):
        assert respuesta.status_code == 400
        assert respuesta.json()["error"]["code"] == "token_invalido"
    assert con_uid_invalido.json() == con_token_manipulado.json() == sin_token.json()


def test_contrasena_debil_y_confirmacion_distinta_dan_datos_invalidos(usuario_cliente):
    _solicitar(_cliente(), usuario_cliente.email)
    uid, token = _uid_token(mail.outbox[0])

    debil = _confirmar(_cliente(), _datos_confirmar(uid, token, "123456"))
    distinta = _confirmar(
        _cliente(), _datos_confirmar(uid, token, PASSWORD_NUEVA, "OtraClave#2026")
    )

    for respuesta in (debil, distinta):
        assert respuesta.status_code == 400
        assert respuesta.json()["error"]["code"] == "datos_invalidos"
    assert "new_password" in debil.json()["error"]["details"]
    assert "new_password_confirm" in distinta.json()["error"]["details"]


def test_reset_revoca_los_tokens_previos_de_api(usuario_cliente):
    Token.objects.create(user=usuario_cliente, key="token-previo")
    _solicitar(_cliente(), usuario_cliente.email)
    uid, token = _uid_token(mail.outbox[0])

    assert _confirmar(_cliente(), _datos_confirmar(uid, token)).status_code == 200
    assert not Token.objects.filter(user=usuario_cliente).exists()
    assert (
        _cliente().post(
            LOGIN_URL,
            {"username": usuario_cliente.username, "password": PASSWORD_NUEVA},
            format="json",
        ).status_code
        == 200
    )


def test_confirmacion_no_inicia_sesion(usuario_cliente):
    _solicitar(_cliente(), usuario_cliente.email)
    uid, token = _uid_token(mail.outbox[0])
    cliente = _cliente()

    respuesta = _confirmar(cliente, _datos_confirmar(uid, token))
    assert respuesta.status_code == 200
    assert "sessionid" not in respuesta.cookies
    assert cliente.get(ME_URL).status_code == 401


@override_settings(REST_FRAMEWORK=_rates(password_reset="2/hour"))
def test_limite_por_ip_devuelve_429_con_retry_after(usuario_cliente):
    cliente = _cliente(ip="10.0.0.1")
    assert _solicitar(cliente, usuario_cliente.email).status_code == 200
    assert _solicitar(cliente, usuario_cliente.email).status_code == 200

    tercera = _solicitar(cliente, usuario_cliente.email)
    assert tercera.status_code == 429
    assert tercera.json()["error"]["code"] == "demasiadas_solicitudes"
    assert int(tercera["Retry-After"]) >= 1


@override_settings(PASSWORD_RESET_MAX_EMAILS_PER_HOUR=1)
def test_tope_por_correo_no_cambia_la_respuesta(usuario_cliente):
    cliente = _cliente()
    primera = _solicitar(cliente, usuario_cliente.email)
    segunda = _solicitar(cliente, usuario_cliente.email)

    assert primera.status_code == segunda.status_code == 200
    assert primera.json() == segunda.json()
    assert len(mail.outbox) == 1


def test_variables_smtp_y_de_url_se_leen_del_entorno(monkeypatch):
    monkeypatch.delenv("EMAIL_BACKEND", raising=False)
    valores = {
        "EMAIL_HOST": "smtp.example.com",
        "EMAIL_PORT": "587",
        "EMAIL_HOST_USER": "usuario@example.com",
        "EMAIL_HOST_PASSWORD": "secreto",
        "EMAIL_USE_TLS": "True",
        "EMAIL_TIMEOUT": "20",
        "DEFAULT_FROM_EMAIL": "Soporte <soporte@example.com>",
        "PASSWORD_RESET_TIMEOUT": "120",
        "FRONTEND_BASE_URL": "https://app.example.com/",
        "PASSWORD_RESET_FRONTEND_PATH": "/nueva-clave/{uid}/{token}",
        "PASSWORD_RESET_MAX_EMAILS_PER_HOUR": "9",
    }
    for nombre, valor in valores.items():
        monkeypatch.setenv(nombre, valor)

    configuracion = django_settings.configuracion_correo_desde_entorno()
    assert configuracion["EMAIL_BACKEND"] == "django.core.mail.backends.smtp.EmailBackend"
    assert configuracion["EMAIL_HOST"] == "smtp.example.com"
    assert configuracion["EMAIL_PORT"] == 587
    assert configuracion["EMAIL_HOST_USER"] == "usuario@example.com"
    assert configuracion["EMAIL_HOST_PASSWORD"] == "secreto"
    assert configuracion["EMAIL_USE_TLS"] is True
    assert configuracion["EMAIL_TIMEOUT"] == 20
    assert configuracion["DEFAULT_FROM_EMAIL"] == "Soporte <soporte@example.com>"
    assert configuracion["PASSWORD_RESET_TIMEOUT"] == 120
    assert configuracion["FRONTEND_BASE_URL"] == "https://app.example.com"
    assert configuracion["PASSWORD_RESET_FRONTEND_PATH"] == "/nueva-clave/{uid}/{token}"
    assert configuracion["PASSWORD_RESET_MAX_EMAILS_PER_HOUR"] == 9


def test_las_vistas_html_de_password_reset_siguen_funcionando(usuario_cliente):
    cliente = Client()
    assert cliente.get("/cuentas/password_reset/").status_code == 200

    respuesta = cliente.post(
        "/cuentas/password_reset/", {"email": usuario_cliente.email}
    )
    assert respuesta.status_code == 302
    assert len(mail.outbox) == 1
