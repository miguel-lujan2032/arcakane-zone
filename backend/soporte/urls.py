from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

app_name = "soporte"

router = SimpleRouter()
router.register("contactos", views.ContactoViewSet, basename="contacto")

urlpatterns = [
    path("contacto/", views.ContactoCreateView.as_view(), name="contacto"),
    path(
        "mayor-informacion/",
        views.MayorInformacionView.as_view(),
        name="mayor-informacion",
    ),
] + router.urls
