"""Usuarios y roles: consulta administrativa de solo lectura."""
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter

from cuentas.models import Rol, Usuario

from ..filters import BusquedaFilter
from ..permissions import EsAdministrador
from ..serializers import RolSerializer, UsuarioSerializer
from ..utils import parse_bool


class UsuarioViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UsuarioSerializer
    permission_classes = [EsAdministrador]
    filter_backends = [BusquedaFilter, OrderingFilter]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering_fields = ["username", "date_joined", "id"]
    ordering = ["username"]

    def get_queryset(self):
        queryset = Usuario.objects.prefetch_related("roles")
        params = self.request.query_params
        if params.get("rol"):
            queryset = queryset.filter(roles__id=params["rol"]).distinct()
        if params.get("activo") is not None:
            queryset = queryset.filter(is_active=parse_bool(params.get("activo")))
        return queryset


class RolViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Rol.objects.all().order_by("nombre")
    serializer_class = RolSerializer
    permission_classes = [EsAdministrador]
