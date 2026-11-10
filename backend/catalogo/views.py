from decimal import InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from arkane_zone.permissions import IsStaffOrReadOnly

from .models import Categoria, Genero, Plataforma, Videojuego
from .serializers import (
    CategoriaSerializer,
    GeneroSerializer,
    PlataformaSerializer,
    VideojuegoSerializer,
)


def _es_staff(request) -> bool:
    return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class CatalogoBaseViewSet(viewsets.ModelViewSet):
    """CRUD de catálogo: lectura pública y escritura solo para staff."""

    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = self.queryset
        if not _es_staff(self.request):
            qs = qs.filter(activo=True)
        return qs


class CategoriaViewSet(CatalogoBaseViewSet):
    queryset = Categoria.objects.all().order_by("nombre")
    serializer_class = CategoriaSerializer


class PlataformaViewSet(CatalogoBaseViewSet):
    queryset = Plataforma.objects.all().order_by("nombre")
    serializer_class = PlataformaSerializer


class GeneroViewSet(CatalogoBaseViewSet):
    queryset = Genero.objects.all().order_by("nombre")
    serializer_class = GeneroSerializer


class VideojuegoViewSet(viewsets.ModelViewSet):
    """Catálogo de videojuegos con filtros por categoría, plataforma, género y texto."""

    serializer_class = VideojuegoSerializer
    permission_classes = [IsStaffOrReadOnly]

    def get_queryset(self):
        qs = Videojuego.objects.select_related(
            "categoria", "plataforma", "genero"
        ).order_by("titulo")

        if not _es_staff(self.request):
            qs = qs.filter(activo=True)

        params = self.request.query_params

        categoria = params.get("categoria")
        plataforma = params.get("plataforma")
        genero = params.get("genero")
        busqueda = params.get("q", "").strip()

        precio_min = params.get("precio_min")
        precio_max = params.get("precio_max")

        try:
            if categoria:
                qs = qs.filter(categoria_id=categoria)
            if plataforma:
                qs = qs.filter(plataforma_id=plataforma)
            if genero:
                qs = qs.filter(genero_id=genero)
            if busqueda:
                qs = qs.filter(titulo__icontains=busqueda)
            if precio_min:
                qs = qs.filter(precio__gte=precio_min)
            if precio_max:
                qs = qs.filter(precio__lte=precio_max)
        except (TypeError, ValueError, InvalidOperation, DjangoValidationError):
            raise ValidationError(
                {"detail": "Los filtros de categoría, plataforma, género o precio no son válidos."}
            ) from None

        disponible = params.get("disponible")
        if disponible is not None:
            valor = disponible.lower()
            if valor in {"1", "true", "yes"}:
                qs = qs.filter(activo=True, stock__gt=0)
            elif valor in {"0", "false", "no"}:
                qs = qs.filter(stock=0)
            else:
                raise ValidationError(
                    {"disponible": "Use true o false para filtrar por disponibilidad."}
                )

        return qs
