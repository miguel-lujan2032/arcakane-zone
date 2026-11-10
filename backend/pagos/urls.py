from django.urls import path

from . import views

app_name = "pagos"

urlpatterns = [
    path("checkout/<int:pedido_id>/", views.checkout, name="checkout"),
    path("procesar/<int:pedido_id>/", views.procesar_pago, name="procesar"),
]
