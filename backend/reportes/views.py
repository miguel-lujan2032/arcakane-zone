from datetime import date

from django.db.models import Count, Sum
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.models import Categoria, Genero, Plataforma, Videojuego
from pagos.models import Venta
from pedidos.models import Pedido

from .serializers import (
    InventarioSerializer,
    ReporteVideojuegoSerializer,
    VentaReporteSerializer,
)

UMBRAL_BAJO_STOCK = 5

FILTROS_INVENTARIO = {"todos", "agotados", "bajo_stock", "disponibles", "inactivos"}


def _parsear_fecha(valor, nombre):
    """Devuelve (date, error). El error es un mensaje listo para la API."""
    if not valor:
        return None, None
    try:
        return date.fromisoformat(valor), None
    except ValueError:
        return None, f"'{nombre}' debe tener formato AAAA-MM-DD."


class DashboardView(APIView):
    """HU28: métricas generales de la tienda (solo staff)."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        conteo_estados = {
            fila["estado"]: fila["total"]
            for fila in Pedido.objects.values("estado")
            .annotate(total=Count("id"))
            .order_by("estado")
        }

        total_ventas = Venta.objects.aggregate(suma=Sum("total"))["suma"] or 0

        agotados = Videojuego.objects.filter(stock=0, activo=True).order_by("titulo")
        bajo_stock = Videojuego.objects.filter(
            stock__gt=0, stock__lte=UMBRAL_BAJO_STOCK, activo=True
        ).order_by("titulo")

        return Response(
            {
                "total_ventas": total_ventas,
                "num_pedidos_pagados": conteo_estados.get("pagado", 0),
                "pedidos_por_estado": {
                    "pendiente": conteo_estados.get("pendiente", 0),
                    "pagado": conteo_estados.get("pagado", 0),
                    "cancelado": conteo_estados.get("cancelado", 0),
                },
                "agotados": InventarioSerializer(agotados, many=True).data,
                "bajo_stock": InventarioSerializer(bajo_stock, many=True).data,
                "umbral_bajo_stock": UMBRAL_BAJO_STOCK,
            }
        )


class ReporteVentasView(APIView):
    """HU29: ventas registradas con filtro opcional por rango de fechas."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        desde, error_desde = _parsear_fecha(request.query_params.get("desde"), "desde")
        hasta, error_hasta = _parsear_fecha(request.query_params.get("hasta"), "hasta")

        errores = [e for e in (error_desde, error_hasta) if e]
        if desde and hasta and desde > hasta:
            errores.append("'desde' no puede ser posterior a 'hasta'.")
        if errores:
            return Response(
                {"detail": "Parámetros de fecha inválidos.", "errores": errores},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ventas = (
            Venta.objects.select_related("pedido__cliente")
            .prefetch_related("pedido__detalles__videojuego")
            .order_by("-registrada_en")
        )
        if desde:
            ventas = ventas.filter(registrada_en__date__gte=desde)
        if hasta:
            ventas = ventas.filter(registrada_en__date__lte=hasta)

        total_periodo = ventas.aggregate(suma=Sum("total"))["suma"] or 0

        return Response(
            {
                "ventas": VentaReporteSerializer(ventas, many=True).data,
                "total_periodo": total_periodo,
                "num_ventas": ventas.count(),
                "filtros": {
                    "desde": desde.isoformat() if desde else None,
                    "hasta": hasta.isoformat() if hasta else None,
                },
            }
        )


class ReporteInventarioView(APIView):
    """HU30: inventario filtrado por estado de stock."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        filtro = request.query_params.get("filtro", "todos")
        if filtro not in FILTROS_INVENTARIO:
            return Response(
                {
                    "detail": "Filtro inválido.",
                    "opciones": sorted(FILTROS_INVENTARIO),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        videojuegos = Videojuego.objects.select_related(
            "categoria", "plataforma", "genero"
        ).order_by("titulo")

        if filtro == "agotados":
            videojuegos = videojuegos.filter(stock=0)
        elif filtro == "bajo_stock":
            videojuegos = videojuegos.filter(
                stock__gt=0, stock__lte=UMBRAL_BAJO_STOCK
            )
        elif filtro == "disponibles":
            videojuegos = videojuegos.filter(
                stock__gt=UMBRAL_BAJO_STOCK, activo=True
            )
        elif filtro == "inactivos":
            videojuegos = videojuegos.filter(activo=False)

        return Response(
            {
                "filtro": filtro,
                "umbral_bajo_stock": UMBRAL_BAJO_STOCK,
                "total_agotados": Videojuego.objects.filter(
                    stock=0, activo=True
                ).count(),
                "total_bajo_stock": Videojuego.objects.filter(
                    stock__gt=0, stock__lte=UMBRAL_BAJO_STOCK, activo=True
                ).count(),
                "videojuegos": InventarioSerializer(videojuegos, many=True).data,
            }
        )


class ReporteVideojuegosView(APIView):
    """HU31: catálogo con filtros de categoría, género, plataforma y estado."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        params = request.query_params
        categoria_id = params.get("categoria", "")
        genero_id = params.get("genero", "")
        plataforma_id = params.get("plataforma", "")
        estado = params.get("estado", "")
        disponibilidad = params.get("disponibilidad", "")

        videojuegos = Videojuego.objects.select_related(
            "categoria", "plataforma", "genero"
        ).order_by("titulo")

        if estado and estado not in {"activo", "inactivo"}:
            return Response(
                {"detail": "'estado' debe ser 'activo' o 'inactivo'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if disponibilidad and disponibilidad not in {"disponible", "agotado"}:
            return Response(
                {
                    "detail": "'disponibilidad' debe ser 'disponible' o 'agotado'."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if categoria_id:
                videojuegos = videojuegos.filter(categoria_id=categoria_id)
            if genero_id:
                videojuegos = videojuegos.filter(genero_id=genero_id)
            if plataforma_id:
                videojuegos = videojuegos.filter(plataforma_id=plataforma_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Los filtros de categoría, género o plataforma no son válidos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if estado == "activo":
            videojuegos = videojuegos.filter(activo=True)
        elif estado == "inactivo":
            videojuegos = videojuegos.filter(activo=False)
        if disponibilidad == "disponible":
            videojuegos = videojuegos.filter(activo=True, stock__gt=0)
        elif disponibilidad == "agotado":
            videojuegos = videojuegos.filter(stock=0)

        return Response(
            {
                "videojuegos": ReporteVideojuegoSerializer(
                    videojuegos, many=True
                ).data,
                "filtros": {
                    "categoria": categoria_id or None,
                    "genero": genero_id or None,
                    "plataforma": plataforma_id or None,
                    "estado": estado or None,
                    "disponibilidad": disponibilidad or None,
                },
                "opciones": {
                    "categorias": list(
                        Categoria.objects.filter(activo=True)
                        .order_by("nombre")
                        .values("id", "nombre")
                    ),
                    "generos": list(
                        Genero.objects.filter(activo=True)
                        .order_by("nombre")
                        .values("id", "nombre")
                    ),
                    "plataformas": list(
                        Plataforma.objects.filter(activo=True)
                        .order_by("nombre")
                        .values("id", "nombre")
                    ),
                },
            }
        )
