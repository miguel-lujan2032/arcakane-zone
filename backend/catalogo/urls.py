from rest_framework.routers import DefaultRouter

from . import views

app_name = "catalogo"

router = DefaultRouter()
router.register("videojuegos", views.VideojuegoViewSet, basename="videojuego")
router.register("categorias", views.CategoriaViewSet, basename="categoria")
router.register("plataformas", views.PlataformaViewSet, basename="plataforma")
router.register("generos", views.GeneroViewSet, basename="genero")

urlpatterns = router.urls
