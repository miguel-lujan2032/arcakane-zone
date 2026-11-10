from django.urls import path

from . import views

app_name = "pagos"

urlpatterns = [
    path("checkout/<int:pedido_id>/", views.CheckoutView.as_view(), name="checkout"),
    path(
        "procesar/<int:pedido_id>/",
        views.ProcesarPagoView.as_view(),
        name="procesar",
    ),
]
