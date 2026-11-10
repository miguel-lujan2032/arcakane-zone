from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    path("ventas/", views.ReporteVentasView.as_view(), name="ventas"),
    path("inventario/", views.ReporteInventarioView.as_view(), name="inventario"),
    path(
        "videojuegos/",
        views.ReporteVideojuegosView.as_view(),
        name="videojuegos",
    ),
]
