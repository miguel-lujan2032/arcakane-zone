from django.urls import path

from . import views

app_name = "pedidos"

urlpatterns = [
    path("", views.PedidoListView.as_view(), name="lista"),
    path("carrito/", views.CarritoView.as_view(), name="carrito"),
    path("carrito/items/", views.AgregarItemView.as_view(), name="agregar-item"),
    path(
        "carrito/items/<int:detalle_id>/",
        views.ItemCarritoView.as_view(),
        name="item-carrito",
    ),
    path("<int:pk>/", views.PedidoDetailView.as_view(), name="detalle"),
    path("<int:pk>/cancelar/", views.CancelarPedidoView.as_view(), name="cancelar"),
]
