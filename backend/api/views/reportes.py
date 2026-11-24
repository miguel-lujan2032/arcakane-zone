"""Reportes de administración expuestos como recursos JSON de solo lectura."""
from django.db.models import Count, Sum
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from catalogo.models import (
    Categoria,
    Genero,
    OfertaVideojuego,
    Plataforma,
)
from pagos.models import Venta
from pedidos.models import Pedido
from reportes.views import UMBRAL_BAJO_STOCK

from ..exceptions import respuesta_exitosa
from ..pagination import StandardResultsSetPagination
from ..permissions import EsAdministrador
from ..serializers import OfertaVideojuegoSerializer, VentaSerializer


def _ofertas_catalogo():
    return OfertaVideojuego.objects.select_related(
        "videojuego", "plataforma", "estado_publicacion"
    ).prefetch_related("videojuego__categorias", "videojuego__generos")


def _monto(valor) -> str:
    """Normaliza importes a dos decimales en las respuestas JSON."""
    return f"{valor:.2f}"


class ReporteBaseView(GenericAPIView):
    permission_classes = [EsAdministrador]
    pagination_class = StandardResultsSetPagination

    def _paginar(self, queryset, serializer_class, **extra):
        pagina = self.paginate_queryset(queryset)
        if pagina is None:
            resultados = serializer_class(
                queryset, many=True, context=self.get_serializer_context()
            ).data
            return respuesta_exitosa({"resultados": resultados, **extra})

        resultados = serializer_class(
            pagina, many=True, context=self.get_serializer_context()
        ).data
        paginador = self.paginator
        return respuesta_exitosa(
            {"resultados": resultados, **extra},
            pagination=paginador.metadatos(),
        )


class DashboardView(ReporteBaseView):
    serializer_class = OfertaVideojuegoSerializer

    def get(self, request):
        estados = (
            Pedido.objects.values("estado")
            .annotate(total=Count("id"))
            .order_by("estado")
        )
        conteo_estados = {e["estado"]: e["total"] for e in estados}
        total_ventas = Venta.objects.aggregate(suma=Sum("total"))["suma"] or 0

        ofertas = _ofertas_catalogo()
        agotados = ofertas.publicadas().filter(stock=0, videojuego__activo=True)
        bajo_stock = ofertas.publicadas().filter(
            stock__gt=0, stock__lte=UMBRAL_BAJO_STOCK, videojuego__activo=True
        )

        return respuesta_exitosa(
            {
                "resumen": {
                    "total_ventas": _monto(total_ventas),
                    "num_pedidos_pagados": conteo_estados.get("pagado", 0),
                    "conteo_pendiente": conteo_estados.get("pendiente", 0),
                    "conteo_pagado": conteo_estados.get("pagado", 0),
                    "conteo_cancelado": conteo_estados.get("cancelado", 0),
                    "umbral_bajo_stock": UMBRAL_BAJO_STOCK,
                },
                "agotados": OfertaVideojuegoSerializer(
                    agotados, many=True, context={"request": request}
                ).data,
                "bajo_stock": OfertaVideojuegoSerializer(
                    bajo_stock, many=True, context={"request": request}
                ).data,
            }
        )


class ReporteVentasQuerySerializer(serializers.Serializer):
    desde = serializers.DateField(required=False)
    hasta = serializers.DateField(required=False)
    cliente = serializers.IntegerField(required=False, min_value=1)

    def validate(self, attrs):
        desde, hasta = attrs.get("desde"), attrs.get("hasta")
        if desde and hasta and desde > hasta:
            raise serializers.ValidationError(
                {"hasta": "La fecha final no puede ser anterior a la inicial."}
            )
        return attrs


class ReporteVentasView(ReporteBaseView):
    serializer_class = VentaSerializer

    def get(self, request):
        params = ReporteVentasQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        datos = params.validated_data

        ventas = Venta.objects.select_related("pedido", "pedido__cliente").prefetch_related(
            "pedido__detalles__oferta__videojuego",
            "pedido__detalles__oferta__plataforma",
            "pedido__detalles__oferta__estado_publicacion",
        )
        if datos.get("desde"):
            ventas = ventas.filter(registrada_en__date__gte=datos["desde"])
        if datos.get("hasta"):
            ventas = ventas.filter(registrada_en__date__lte=datos["hasta"])
        if datos.get("cliente"):
            ventas = ventas.filter(pedido__cliente_id=datos["cliente"])

        total_periodo = ventas.aggregate(suma=Sum("total"))["suma"] or 0
        return self._paginar(
            ventas.order_by("-registrada_en"),
            VentaSerializer,
            resumen={
                "total_periodo": _monto(total_periodo),
                "cantidad_ventas": ventas.count(),
                "desde": datos.get("desde"),
                "hasta": datos.get("hasta"),
            },
        )


class ReporteInventarioQuerySerializer(serializers.Serializer):
    filtro = serializers.ChoiceField(
        choices=["todos", "agotados", "bajo_stock", "disponibles", "inactivas"],
        default="todos",
    )


class ReporteInventarioView(ReporteBaseView):
    serializer_class = OfertaVideojuegoSerializer

    def get(self, request):
        params = ReporteInventarioQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        filtro = params.validated_data["filtro"]

        ofertas = _ofertas_catalogo().order_by("videojuego__titulo", "plataforma__nombre")
        if filtro == "agotados":
            ofertas = ofertas.publicadas().filter(stock=0, videojuego__activo=True)
        elif filtro == "bajo_stock":
            ofertas = ofertas.publicadas().filter(
                stock__gt=0, stock__lte=UMBRAL_BAJO_STOCK, videojuego__activo=True
            )
        elif filtro == "disponibles":
            ofertas = ofertas.publicadas().filter(
                stock__gt=UMBRAL_BAJO_STOCK, videojuego__activo=True
            )
        elif filtro == "inactivas":
            ofertas = ofertas.exclude(estado_publicacion_id="publicado")

        return self._paginar(
            ofertas,
            OfertaVideojuegoSerializer,
            resumen={
                "filtro": filtro,
                "umbral_bajo_stock": UMBRAL_BAJO_STOCK,
                "total_agotados": _ofertas_catalogo()
                .publicadas()
                .filter(stock=0, videojuego__activo=True)
                .count(),
                "total_bajo_stock": _ofertas_catalogo()
                .publicadas()
                .filter(stock__gt=0, stock__lte=UMBRAL_BAJO_STOCK, videojuego__activo=True)
                .count(),
            },
        )


class ReporteVideojuegosQuerySerializer(serializers.Serializer):
    categoria = serializers.IntegerField(required=False, min_value=1)
    genero = serializers.IntegerField(required=False, min_value=1)
    plataforma = serializers.IntegerField(required=False, min_value=1)
    estado = serializers.ChoiceField(choices=["activo", "inactivo"], required=False)
    disponibilidad = serializers.ChoiceField(
        choices=["disponible", "agotado"], required=False
    )


class ReporteVideojuegosView(ReporteBaseView):
    serializer_class = OfertaVideojuegoSerializer

    def get(self, request):
        params = ReporteVideojuegosQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        datos = params.validated_data

        ofertas = _ofertas_catalogo().order_by("videojuego__titulo", "plataforma__nombre")
        if datos.get("categoria"):
            ofertas = ofertas.filter(videojuego__categorias__id=datos["categoria"])
        if datos.get("genero"):
            ofertas = ofertas.filter(videojuego__generos__id=datos["genero"])
        if datos.get("plataforma"):
            ofertas = ofertas.filter(plataforma_id=datos["plataforma"])
        if datos.get("estado") == "activo":
            ofertas = ofertas.filter(videojuego__activo=True)
        elif datos.get("estado") == "inactivo":
            ofertas = ofertas.filter(videojuego__activo=False)
        if datos.get("disponibilidad") == "disponible":
            ofertas = ofertas.publicadas().filter(stock__gt=0, videojuego__activo=True)
        elif datos.get("disponibilidad") == "agotado":
            ofertas = ofertas.publicadas().filter(stock=0, videojuego__activo=True)

        # Los filtros por catálogo M2M no deben duplicar ofertas paginadas.
        ofertas = ofertas.distinct()
        return self._paginar(
            ofertas,
            OfertaVideojuegoSerializer,
            resumen={
                "filtros": {
                    "categoria": datos.get("categoria"),
                    "genero": datos.get("genero"),
                    "plataforma": datos.get("plataforma"),
                    "estado": datos.get("estado"),
                    "disponibilidad": datos.get("disponibilidad"),
                },
                "categorias": Categoria.objects.filter(activo=True).count(),
                "generos": Genero.objects.filter(activo=True).count(),
                "plataformas": Plataforma.objects.filter(activo=True).count(),
            },
        )
