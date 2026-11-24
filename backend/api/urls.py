"""Rutas versionadas de la API REST.

Convenciones:
- Sustantivos en plural y en español, alineados con el dominio.
- Barra final en todas las colecciones y detalles.
- Recursos anidados cuando existe una relación clara
  (``/catalogo/videojuegos/{id}/ofertas/``).
"""
from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views.auth import (
    CambioPasswordView,
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetView,
    RegistroView,
)
from .views.base import ApiNotFoundView, ApiRootView, HealthView
from .views.carrito import CarritoItemDetalleView, CarritoItemsView, CarritoView
from .views.catalogo import (
    CategoriaViewSet,
    GeneroViewSet,
    OfertaVideojuegoViewSet,
    PlataformaViewSet,
    VideojuegoViewSet,
)
from .views.pagos import PagoViewSet, VentaViewSet
from .views.pedidos import PedidoViewSet
from .views.reportes import (
    DashboardView,
    ReporteInventarioView,
    ReporteVentasView,
    ReporteVideojuegosView,
)
from .views.soporte import ContactoViewSet, MayorInformacionView
from .views.usuarios import RolViewSet, UsuarioViewSet

router = SimpleRouter(trailing_slash=True)
router.register("catalogo/categorias", CategoriaViewSet, basename="categoria")
router.register("catalogo/plataformas", PlataformaViewSet, basename="plataforma")
router.register("catalogo/generos", GeneroViewSet, basename="genero")
router.register("catalogo/videojuegos", VideojuegoViewSet, basename="videojuego")
router.register("catalogo/ofertas", OfertaVideojuegoViewSet, basename="oferta")
router.register("pedidos", PedidoViewSet, basename="pedido")
router.register("pagos", PagoViewSet, basename="pago")
router.register("ventas", VentaViewSet, basename="venta")
router.register("soporte/contactos", ContactoViewSet, basename="contacto")
router.register("usuarios", UsuarioViewSet, basename="usuario")
router.register("roles", RolViewSet, basename="rol")

urlpatterns = [
    path("", ApiRootView.as_view(), name="api-root"),
    path("health/", HealthView.as_view(), name="api-health"),
    # Autenticación y perfil
    path("auth/registro/", RegistroView.as_view(), name="auth-registro"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path(
        "auth/me/password/",
        CambioPasswordView.as_view(),
        name="auth-cambiar-password",
    ),
    path("auth/csrf/", CsrfView.as_view(), name="auth-csrf"),
    path(
        "auth/password-reset/",
        PasswordResetView.as_view(),
        name="auth-password-reset",
    ),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    # Carrito
    path("carrito/", CarritoView.as_view(), name="carrito"),
    path("carrito/items/", CarritoItemsView.as_view(), name="carrito-items"),
    path(
        "carrito/items/<int:pk>/",
        CarritoItemDetalleView.as_view(),
        name="carrito-item-detalle",
    ),
    # Reportes (solo staff)
    path("reportes/dashboard/", DashboardView.as_view(), name="reporte-dashboard"),
    path("reportes/ventas/", ReporteVentasView.as_view(), name="reporte-ventas"),
    path(
        "reportes/inventario/",
        ReporteInventarioView.as_view(),
        name="reporte-inventario",
    ),
    path(
        "reportes/videojuegos/",
        ReporteVideojuegosView.as_view(),
        name="reporte-videojuegos",
    ),
    # Soporte
    path(
        "soporte/mayor-informacion/",
        MayorInformacionView.as_view(),
        name="soporte-mayor-informacion",
    ),
    path("", include(router.urls)),
    # Cualquier ruta no registrada bajo /api/v1/ responde JSON 404.
    path("<path:ruta>", ApiNotFoundView.as_view(), name="api-not-found"),
]
