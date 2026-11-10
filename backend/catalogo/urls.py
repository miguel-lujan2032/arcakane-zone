from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("", views.lista_videojuegos, name="lista"),
    path("<int:pk>/", views.detalle_videojuego, name="detalle"),
]
