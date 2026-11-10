from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from pedidos.models import Pedido
from pedidos.serializers import PedidoSerializer
from pedidos.services import validar_para_checkout

from .models import Pago
from .serializers import PagoSerializer
from .services import procesar_pago_simulado


def _serializar_pedido(pedido, request):
    return PedidoSerializer(pedido, context={"request": request}).data


class CheckoutView(APIView):
    """Resumen y validación del pedido antes de pagar."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pedido_id):
        pedido = get_object_or_404(
            Pedido,
            pk=pedido_id,
            cliente=request.user,
            estado=Pedido.Estado.PENDIENTE,
        )
        errores = validar_para_checkout(pedido)
        return Response(
            {
                "pedido": _serializar_pedido(pedido, request),
                "valido": not errores,
                "errores": errores,
            }
        )


class ProcesarPagoView(APIView):
    """Ejecuta el pago simulado. No recibe datos de tarjeta."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pedido_id):
        pedido = get_object_or_404(
            Pedido,
            pk=pedido_id,
            cliente=request.user,
            estado=Pedido.Estado.PENDIENTE,
        )

        errores = validar_para_checkout(pedido)
        if errores:
            return Response(
                {"detail": "El pedido no está listo para pagar.", "errores": errores},
                status=status.HTTP_400_BAD_REQUEST,
            )

        aprobado, mensaje = procesar_pago_simulado(pedido)

        pedido.refresh_from_db()
        pago = Pago.objects.filter(pedido=pedido).first()
        return Response(
            {
                "aprobado": aprobado,
                "detail": mensaje,
                "pago": PagoSerializer(pago).data if pago else None,
                "pedido": _serializar_pedido(pedido, request),
            }
        )
