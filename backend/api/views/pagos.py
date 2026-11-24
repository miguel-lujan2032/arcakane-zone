"""Pagos simulados y ventas registradas."""
from rest_framework import mixins, status, viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated

from pagos.models import IntentoPago, Venta
from pagos.services import procesar_pago_simulado
from pedidos.services import validar_para_checkout

from ..exceptions import ErrorDeNegocio, respuesta_error, respuesta_exitosa
from ..permissions import EsAdministrador
from ..serializers import PagoCreateSerializer, PagoSerializer, VentaSerializer
from ..utils import es_administrador, parse_fecha


class PagoViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = IntentoPago.objects.select_related("pedido", "pedido__cliente").order_by(
            "-creado_en", "-id"
        )
        if not es_administrador(self.request.user):
            queryset = queryset.filter(pedido__cliente=self.request.user)
        return queryset

    def get_serializer_class(self):
        if self.action == "create":
            return PagoCreateSerializer
        return PagoSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pedido = serializer.validated_data["pedido"]

        if not es_administrador(request.user) and pedido.cliente_id != request.user.id:
            raise NotFound("El pedido no existe.")
        if pedido.estado_id != "pendiente":
            raise ErrorDeNegocio("El pedido no está en estado pendiente.")

        errores = validar_para_checkout(pedido)
        if errores:
            raise ErrorDeNegocio(
                "El pedido no está listo para pagar.",
                extra={"errores": errores},
            )

        exito, mensaje = procesar_pago_simulado(pedido)
        # Con varios intentos, el cliente ve siempre el último (el aprobado
        # cuando el pago se completó; el rechazo si la pasarela lo denegó).
        pago = (
            IntentoPago.objects.select_related("pedido", "pedido__cliente")
            .filter(pedido=pedido)
            .order_by("-creado_en", "-pk")
            .first()
        )

        if pago is None:
            # La operación se bloqueó antes de registrar el intento de pago.
            raise ErrorDeNegocio(mensaje)

        if not exito:
            # Existe el registro: la pasarela simulada rechazó el pago (402).
            return respuesta_error(
                "pago_rechazado",
                mensaje,
                detalles=PagoSerializer(pago, context={"request": request}).data,
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
            )

        return respuesta_exitosa(
            PagoSerializer(pago, context={"request": request}).data,
            message=mensaje,
            status_code=status.HTTP_201_CREATED,
        )


class VentaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VentaSerializer
    permission_classes = [EsAdministrador]

    def get_queryset(self):
        queryset = (
            Venta.objects.select_related("pedido", "pedido__cliente")
            .prefetch_related(
                "pedido__detalles__oferta__videojuego",
                "pedido__detalles__oferta__plataforma",
                "pedido__detalles__oferta__estado_publicacion",
            )
            .order_by("-registrada_en", "-id")
        )
        params = self.request.query_params
        desde = params.get("desde")
        hasta = params.get("hasta")
        cliente = params.get("cliente")

        try:
            if desde:
                queryset = queryset.filter(registrada_en__date__gte=parse_fecha(desde, "desde"))
            if hasta:
                queryset = queryset.filter(registrada_en__date__lte=parse_fecha(hasta, "hasta"))
        except ValueError as exc:
            raise ValidationError({"fechas": str(exc)}) from exc

        if cliente:
            queryset = queryset.filter(pedido__cliente_id=cliente)
        return queryset
