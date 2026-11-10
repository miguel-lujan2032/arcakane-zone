from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from .views import health

urlpatterns = [
    path("api/health/", health, name="health"),
    path("api/v1/auth/", include("cuentas.urls")),
    path("api/v1/catalogo/", include("catalogo.urls")),
    path("api/v1/pedidos/", include("pedidos.urls")),
    path("api/v1/pagos/", include("pagos.urls")),
    path("api/v1/reportes/", include("reportes.urls")),
    path("api/v1/soporte/", include("soporte.urls")),
]

# En desarrollo la API puede servir los archivos de medios locales.
# En producción se espera S3/Supabase Storage.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
