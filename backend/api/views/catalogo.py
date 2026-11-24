"""Recursos del catálogo: categorías, plataformas, géneros, títulos y ofertas."""
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny

from catalogo.models import (
    Categoria,
    EstadoPublicacion,
    Genero,
    OfertaVideojuego,
    Plataforma,
    Videojuego,
)

from ..exceptions import respuesta_exitosa
from ..filters import BusquedaFilter
from ..permissions import LecturaPublicaEscrituraAdmin
from ..serializers import (
    CategoriaSerializer,
    GeneroSerializer,
    OfertaVideojuegoSerializer,
    PlataformaSerializer,
    VideojuegoSerializer,
)
from ..utils import es_administrador, parse_bool


class _CatalogoBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [LecturaPublicaEscrituraAdmin]
    filter_backends = [BusquedaFilter, OrderingFilter]

    def _solo_activos_para_publico(self, queryset, campo="activo"):
        if es_administrador(self.request.user):
            valor = self.request.query_params.get(campo)
            if valor is not None:
                return queryset.filter(**{campo: parse_bool(valor)})
            return queryset
        return queryset.filter(**{campo: True})


class CategoriaViewSet(_CatalogoBaseViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    search_fields = ["nombre", "descripcion"]
    ordering_fields = ["nombre", "id"]
    ordering = ["nombre"]

    def get_queryset(self):
        return self._solo_activos_para_publico(Categoria.objects.all())


class PlataformaViewSet(_CatalogoBaseViewSet):
    queryset = Plataforma.objects.all()
    serializer_class = PlataformaSerializer
    search_fields = ["nombre", "descripcion"]
    ordering_fields = ["nombre", "id"]
    ordering = ["nombre"]

    def get_queryset(self):
        return self._solo_activos_para_publico(Plataforma.objects.all())


class GeneroViewSet(_CatalogoBaseViewSet):
    queryset = Genero.objects.all()
    serializer_class = GeneroSerializer
    search_fields = ["nombre", "descripcion"]
    ordering_fields = ["nombre", "id"]
    ordering = ["nombre"]

    def get_queryset(self):
        return self._solo_activos_para_publico(Genero.objects.all())


class VideojuegoViewSet(_CatalogoBaseViewSet):
    serializer_class = VideojuegoSerializer
    search_fields = ["titulo", "descripcion", "categorias__nombre", "generos__nombre"]
    ordering_fields = ["titulo", "fecha_lanzamiento", "creado_en", "id"]
    ordering = ["titulo"]

    def get_queryset(self):
        queryset = Videojuego.objects.prefetch_related(
            "categorias",
            "generos",
            "ofertas__plataforma",
            "ofertas__estado_publicacion",
        )
        queryset = self._solo_activos_para_publico(queryset)

        params = self.request.query_params
        categoria = params.get("categoria")
        genero = params.get("genero")
        plataforma = params.get("plataforma")
        disponible = params.get("disponible")

        # Los filtros M2M pueden repetir filas: ``distinct`` protege la paginación.
        if categoria:
            queryset = queryset.filter(categorias__id=categoria)
        if genero:
            queryset = queryset.filter(generos__id=genero)
        condiciones_oferta = Q()
        if plataforma:
            condiciones_oferta &= Q(ofertas__plataforma_id=plataforma)
        if disponible is not None:
            if parse_bool(disponible):
                condiciones_oferta &= Q(
                    ofertas__estado_publicacion_id="publicado",
                    ofertas__stock__gt=0,
                )
            else:
                queryset = queryset.exclude(
                    ofertas__estado_publicacion_id="publicado",
                    ofertas__stock__gt=0,
                )
        if condiciones_oferta:
            queryset = queryset.filter(condiciones_oferta)
        return queryset.distinct()

    @action(detail=True, methods=["get"], url_path="ofertas")
    def ofertas(self, request, pk=None):
        videojuego = self.get_object()
        ofertas = videojuego.ofertas.select_related("plataforma", "videojuego")
        if not es_administrador(request.user):
            ofertas = ofertas.publicadas().filter(videojuego__activo=True)
        ofertas = ofertas.order_by("precio_vigente")
        pagina = self.paginate_queryset(ofertas)
        if pagina is not None:
            serializer = OfertaVideojuegoSerializer(
                pagina, many=True, context=self.get_serializer_context()
            )
            return self.get_paginated_response(serializer.data)
        serializer = OfertaVideojuegoSerializer(
            ofertas, many=True, context=self.get_serializer_context()
        )
        return respuesta_exitosa(serializer.data)


class OfertaVideojuegoViewSet(_CatalogoBaseViewSet):
    serializer_class = OfertaVideojuegoSerializer
    search_fields = ["sku", "videojuego__titulo", "plataforma__nombre"]
    ordering_fields = ["precio_vigente", "stock", "creado_en", "id"]
    ordering = ["videojuego__titulo", "plataforma__nombre"]

    def get_queryset(self):
        queryset = OfertaVideojuego.objects.select_related(
            "videojuego", "plataforma", "estado_publicacion"
        ).prefetch_related("videojuego__categorias", "videojuego__generos")
        admin = es_administrador(self.request.user)

        if not admin:
            queryset = queryset.publicadas().filter(videojuego__activo=True)

        params = self.request.query_params
        videojuego = params.get("videojuego")
        plataforma = params.get("plataforma")
        categoria = params.get("categoria")
        genero = params.get("genero")
        estado = params.get("estado_publicacion")
        disponible = params.get("disponible")

        if videojuego:
            queryset = queryset.filter(videojuego_id=videojuego)
        if plataforma:
            queryset = queryset.filter(plataforma_id=plataforma)
        if categoria:
            queryset = queryset.filter(videojuego__categorias__id=categoria)
        if genero:
            queryset = queryset.filter(videojuego__generos__id=genero)
        if estado and admin:
            codigos = list(
                EstadoPublicacion.objects.values_list("codigo", flat=True)
            )
            if estado not in codigos:
                raise ValidationError(
                    {
                        "estado_publicacion": (
                            "Valor inválido. Opciones: " + ", ".join(codigos)
                        )
                    }
                )
            queryset = queryset.filter(estado_publicacion_id=estado)
        if disponible is not None:
            if parse_bool(disponible):
                queryset = queryset.filter(stock__gt=0)
            else:
                queryset = queryset.filter(stock=0)
        return queryset.distinct()
