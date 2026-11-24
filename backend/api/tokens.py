"""Punto único para revocar los tokens de API de un usuario.

En este issue los tokens siguen siendo los de DRF. Otro issue puede cambiar
esta función sin tocar las vistas que la llaman.
"""
from rest_framework.authtoken.models import Token


def revocar_tokens_api(usuario):
    """Elimina todos los tokens de API del usuario."""
    Token.objects.filter(user=usuario).delete()
