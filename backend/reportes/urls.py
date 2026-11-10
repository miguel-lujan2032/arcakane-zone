from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("ventas/", views.reporte_ventas, name="ventas"),
    path("inventario/", views.reporte_inventario, name="inventario"),
    path("videojuegos/", views.reporte_videojuegos, name="videojuegos"),
]
