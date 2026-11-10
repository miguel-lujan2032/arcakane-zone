from django.urls import path

from . import views

app_name = "soporte"

urlpatterns = [
    path("contacto/", views.contacto, name="contacto"),
    path("mayor-informacion/", views.mayor_informacion, name="mayor_informacion"),
    path("ayuda/", views.ayuda, name="ayuda"),
]
