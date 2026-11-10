from django.urls import path

from . import views

app_name = "pedidos"

urlpatterns = [
    path("carrito/", views.carrito, name="carrito"),
    path("carrito/agregar/<int:oferta_id>/", views.agregar_al_carrito, name="agregar_al_carrito"),
    path("carrito/actualizar/<int:detalle_id>/", views.actualizar_item, name="actualizar_item"),
    path("carrito/quitar/<int:detalle_id>/", views.quitar_del_carrito, name="quitar_del_carrito"),
    path("mis-pedidos/", views.mis_pedidos, name="mis_pedidos"),
    path("<int:pk>/", views.detalle_pedido, name="detalle"),
    path("<int:pk>/cancelar/", views.cancelar_pedido_view, name="cancelar"),
]
