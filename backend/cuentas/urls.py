from django.urls import path

from . import views

app_name = "cuentas"

urlpatterns = [
    path("register/", views.RegistroView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("me/", views.MeView.as_view(), name="me"),
    path("change-password/", views.CambioPasswordView.as_view(), name="change-password"),
]
