from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from catalogo.views import lista_videojuegos

urlpatterns = [
    path("admin/", admin.site.urls),
    # Auth de Django (login/logout/password reset)
    path("cuentas/", include("django.contrib.auth.urls")),
    # Apps del proyecto
    path("cuentas/", include("cuentas.urls")),
    path("catalogo/", include("catalogo.urls")),
    path("pedidos/", include("pedidos.urls")),
    path("pagos/", include("pagos.urls")),
    path("reportes/", include("reportes.urls")),
    path("soporte/", include("soporte.urls")),
    # Raíz apunta al catálogo
    path("", lista_videojuegos, name="home"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
