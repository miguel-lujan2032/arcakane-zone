from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Pedido
from .serializers import (
    ActualizarItemSerializer,
    AgregarItemSerializer,
    PedidoSerializer,
)
from .services import (
    actualizar_cantidad,
    agregar_o_incrementar,
    cancelar_pedido,
    get_or_create_carrito,
    quitar_item,
)


def _serializar_pedido(pedido, request):
    return PedidoSerializer(pedido, context={"request": request}).data


class CarritoView(APIView):
    """Devuelve el carrito (pedido pendiente) del usuario autenticado."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        pedido = get_or_create_carrito(request.user)
        return Response(_serializar_pedido(pedido, request))


class AgregarItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AgregarItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        exito, mensaje = agregar_o_incrementar(
            request.user,
            serializer.validated_data["videojuego_id"],
            serializer.validated_data["cantidad"],
        )
        if not exito:
            return Response(
                {"detail": mensaje}, status=status.HTTP_400_BAD_REQUEST
            )

        pedido = get_or_create_carrito(request.user)
        return Response(
            {"detail": mensaje, "pedido": _serializar_pedido(pedido, request)},
            status=status.HTTP_201_CREATED,
        )


class ItemCarritoView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, detalle_id):
        serializer = ActualizarItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        exito, mensaje = actualizar_cantidad(
            request.user, detalle_id, serializer.validated_data["cantidad"]
        )
        if not exito:
            return Response(
                {"detail": mensaje}, status=status.HTTP_400_BAD_REQUEST
            )

        pedido = get_or_create_carrito(request.user)
        return Response(
            {"detail": mensaje, "pedido": _serializar_pedido(pedido, request)}
        )

    def delete(self, request, detalle_id):
        exito, mensaje = quitar_item(request.user, detalle_id)
        if not exito:
            return Response(
                {"detail": mensaje}, status=status.HTTP_404_NOT_FOUND
            )

        pedido = get_or_create_carrito(request.user)
        return Response(
            {"detail": mensaje, "pedido": _serializar_pedido(pedido, request)}
        )


class PedidoListView(ListAPIView):
    """Historial de pedidos del cliente, sin carritos vacíos."""

    permission_classes = [IsAuthenticated]
    serializer_class = PedidoSerializer

    def get_queryset(self):
        return (
            Pedido.objects.filter(cliente=self.request.user)
            .annotate(num_detalles=Count("detalles"))
            .exclude(num_detalles=0)
            .prefetch_related("detalles__videojuego")
            .order_by("-creado_en")
        )


class PedidoDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PedidoSerializer

    def get_queryset(self):
        return Pedido.objects.filter(cliente=self.request.user).prefetch_related(
            "detalles__videojuego"
        )


class CancelarPedidoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        pedido = get_object_or_404(Pedido, pk=pk, cliente=request.user)
        exito, mensaje = cancelar_pedido(pedido)
        if not exito:
            return Response(
                {"detail": mensaje}, status=status.HTTP_400_BAD_REQUEST
            )

        pedido.refresh_from_db()
        return Response(
            {"detail": mensaje, "pedido": _serializar_pedido(pedido, request)}
        )
