from rest_framework import mixins, status, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Contacto
from .serializers import (
    ContactoAdminSerializer,
    ContactoSerializer,
    MayorInformacionSerializer,
)


class ContactoCreateView(APIView):
    """HU32: formulario de contacto general (público)."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ContactoSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        contacto = serializer.save()
        return Response(
            {
                "detail": "Tu mensaje fue enviado. Te responderemos pronto.",
                "contacto": ContactoSerializer(contacto).data,
            },
            status=status.HTTP_201_CREATED,
        )


class MayorInformacionView(APIView):
    """HU33: el visitante deja sus datos para recibir información."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = MayorInformacionSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        contacto = serializer.save()
        return Response(
            {
                "detail": "¡Gracias! Nos pondremos en contacto contigo pronto.",
                "contacto": ContactoAdminSerializer(contacto).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ContactoViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Bandeja de contactos para staff; permite marcar como atendido."""

    queryset = Contacto.objects.select_related("usuario").all()
    serializer_class = ContactoAdminSerializer
    permission_classes = [IsAdminUser]
    http_method_names = ["get", "patch", "head", "options"]
