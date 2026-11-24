"""Carrito de compras del usuario autenticado."""
from django.db import transaction
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from pedidos.models import DetallePedido, Pedido
from pedidos.services import (
    actualizar_cantidad,
    agregar_o_incrementar,
    get_or_create_carrito,
    quitar_item,
)

from ..exceptions import ErrorDeNegocio, respuesta_exitosa
from ..serializers import (
    CarritoItemCreateSerializer,
    CarritoItemUpdateSerializer,
    CarritoSerializer,
    DetallePedidoSerializer,
)


def _carrito_pendiente(usuario):
    return (
        Pedido.objects.filter(cliente=usuario, estado_id="pendiente")
        .prefetch_related("detalles__oferta__videojuego", "detalles__oferta__plataforma")
        .first()
    )


def _detalle_del_carrito(usuario, pk):
    try:
        return DetallePedido.objects.select_related(
            "oferta__videojuego", "oferta__plataforma"
        ).get(
            pk=pk,
            pedido__cliente=usuario,
            pedido__estado_id="pendiente",
        )
    except DetallePedido.DoesNotExist as exc:
        raise NotFound("El ítem del carrito no existe.") from exc


def _serializar_carrito(pedido, request):
    if pedido is None:
        return {
            "id": None,
            "estado": "pendiente",
            "total": "0.00",
            "total_items": 0,
            "detalles": [],
        }
    return CarritoSerializer(pedido, context={"request": request}).data


class CarritoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pedido = _carrito_pendiente(request.user)
        return respuesta_exitosa(_serializar_carrito(pedido, request))

    @transaction.atomic
    def delete(self, request):
        pedido = _carrito_pendiente(request.user)
        if pedido is not None:
            pedido.detalles.all().delete()
        return respuesta_exitosa(
            message="Carrito vaciado correctamente.",
        )


class CarritoItemsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CarritoItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        oferta = serializer.validated_data["oferta"]
        cantidad = serializer.validated_data["cantidad"]

        exito, mensaje = agregar_o_incrementar(request.user, oferta.pk, cantidad)
        if not exito:
            raise ErrorDeNegocio(mensaje)

        pedido = get_or_create_carrito(request.user)
        detalle = _detalle_del_carrito(request.user, pedido.detalles.get(oferta=oferta).pk)
        return respuesta_exitosa(
            DetallePedidoSerializer(detalle, context={"request": request}).data,
            message=mensaje,
            status_code=status.HTTP_201_CREATED,
        )


class CarritoItemDetalleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        detalle = _detalle_del_carrito(request.user, pk)
        return respuesta_exitosa(
            DetallePedidoSerializer(detalle, context={"request": request}).data
        )

    def patch(self, request, pk):
        detalle = _detalle_del_carrito(request.user, pk)
        serializer = CarritoItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cantidad = serializer.validated_data["cantidad"]

        exito, mensaje = actualizar_cantidad(request.user, detalle.pk, cantidad)
        if not exito:
            raise ErrorDeNegocio(mensaje)

        if cantidad <= 0:
            return respuesta_exitosa(data=None, message=mensaje)

        detalle.refresh_from_db()
        detalle = _detalle_del_carrito(request.user, pk)
        return respuesta_exitosa(
            DetallePedidoSerializer(detalle, context={"request": request}).data,
            message=mensaje,
        )

    def delete(self, request, pk):
        detalle = _detalle_del_carrito(request.user, pk)
        exito, mensaje = quitar_item(request.user, detalle.pk)
        if not exito:
            raise NotFound(mensaje)
        return respuesta_exitosa(message=mensaje)
