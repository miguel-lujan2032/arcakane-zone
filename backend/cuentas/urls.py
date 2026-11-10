from django.urls import path

from . import views

app_name = "cuentas"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("perfil/", views.perfil, name="perfil"),
    path("perfil/cambiar-password/", views.cambiar_password, name="cambiar_password"),
]
