"""Pedidos del cliente y transiciones de estado."""
from django.db.models import Count, Prefetch
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated

from pagos.models import IntentoPago
from pedidos.models import Pedido
from pedidos.services import cancelar_pedido

from ..exceptions import ErrorDeNegocio, respuesta_exitosa
from ..serializers import PedidoEstadoSerializer, PedidoSerializer, codigos_estado_pedido
from ..utils import es_administrador


class PedidoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "post", "head", "options"]

    def get_queryset(self):
        queryset = (
            Pedido.objects.select_related("cliente", "venta")
            .prefetch_related(
                "intentos_pago",
                Prefetch(
                    "intentos_pago",
                    queryset=IntentoPago.objects.filter(estado_id="aprobado").order_by(
                        "-creado_en", "-pk"
                    ),
                    to_attr="_intentos_aprobados",
                ),
                "detalles__oferta__videojuego",
                "detalles__oferta__plataforma",
                "detalles__oferta__estado_publicacion",
            )
        )
        if not es_administrador(self.request.user):
            queryset = queryset.filter(cliente=self.request.user)

        if self.action == "list":
            # ``annotate`` desactiva el orden por defecto del modelo; se
            # reafirma para que la paginación sea determinista.
            queryset = (
                queryset.annotate(num_detalles=Count("detalles"))
                .exclude(num_detalles=0)
                .order_by("-creado_en", "-id")
            )
        else:
            queryset = queryset.order_by("-creado_en", "-id")

        estado = self.request.query_params.get("estado")
        if estado:
            codigos = codigos_estado_pedido()
            if estado not in codigos:
                raise ValidationError(
                    {
                        "estado": (
                            "Valor inválido. Opciones: " + ", ".join(codigos)
                        )
                    }
                )
            queryset = queryset.filter(estado_id=estado)
        return queryset

    def partial_update(self, request, *args, **kwargs):
        pedido = self.get_object()
        if set(request.data.keys()) - {"estado"}:
            raise ValidationError(
                {
                    "detail": (
                        "Solo se puede modificar el estado del pedido mediante "
                        "PATCH con el campo 'estado'."
                    )
                }
            )
        serializer = PedidoEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._cancelar(pedido)

    def update(self, request, *args, **kwargs):
        raise ValidationError(
            {"detail": "Usa PATCH para cancelar un pedido pendiente."}
        )

    @action(detail=True, methods=["post"], url_path="cancelar")
    def cancelar(self, request, pk=None):
        """Alias explícito de la transición ``pendiente -> cancelado``."""
        return self._cancelar(self.get_object())

    def _cancelar(self, pedido):
        exito, mensaje = cancelar_pedido(pedido)
        if not exito:
            raise ErrorDeNegocio(mensaje)
        pedido.refresh_from_db()
        pedido = self.get_queryset().get(pk=pedido.pk)
        serializer = self.get_serializer(pedido)
        return respuesta_exitosa(
            serializer.data,
            message=mensaje,
            status_code=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        try:
            return super().retrieve(request, *args, **kwargs)
        except Pedido.DoesNotExist as exc:
            raise NotFound("El pedido no existe.") from exc
