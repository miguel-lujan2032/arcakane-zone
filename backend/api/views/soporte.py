"""Soporte: contactos y solicitudes de información."""
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from soporte.models import Contacto

from ..exceptions import respuesta_exitosa
from ..permissions import PermisoContacto
from ..serializers import ContactoSerializer, SolicitudInformacionSerializer
from ..throttling import AnonimoRateThrottle, ContactoRateThrottle, UsuarioRateThrottle
from ..utils import es_administrador


class ContactoViewSet(viewsets.ModelViewSet):
    serializer_class = ContactoSerializer
    permission_classes = [PermisoContacto]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_throttles(self):
        # Solo la creación pública entra en el scope `contacto`; la gestión
        # administrativa sigue con los throttles globales anon/user.
        if self.action == "create":
            return [
                ContactoRateThrottle(),
                AnonimoRateThrottle(),
                UsuarioRateThrottle(),
            ]
        return super().get_throttles()

    def get_queryset(self):
        queryset = Contacto.objects.select_related("usuario")
        if es_administrador(self.request.user):
            return queryset
        if self.request.user.is_authenticated:
            return queryset.filter(usuario=self.request.user)
        return queryset.none()

    def perform_create(self, serializer):
        usuario = self.request.user if self.request.user.is_authenticated else None
        datos = {}
        if usuario is not None:
            datos["usuario"] = usuario
            datos["nombre"] = datos.get("nombre") or serializer.validated_data.get(
                "nombre"
            ) or usuario.get_full_name() or usuario.username
            datos["email"] = datos.get("email") or serializer.validated_data.get(
                "email"
            ) or usuario.email
        datos["asunto"] = serializer.validated_data.get("asunto") or "Contacto"
        serializer.save(**datos)


class MayorInformacionView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ContactoRateThrottle, AnonimoRateThrottle, UsuarioRateThrottle]

    def post(self, request):
        serializer = SolicitudInformacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        usuario = request.user if request.user.is_authenticated else None
        contacto = Contacto.objects.create(
            nombre=datos["nombre"],
            email=datos["email"],
            telefono=datos.get("telefono", ""),
            asunto="Solicitud de información",
            mensaje="",
            usuario=usuario,
        )
        return respuesta_exitosa(
            ContactoSerializer(contacto, context={"request": request}).data,
            message="¡Gracias! Nos pondremos en contacto contigo pronto.",
            status_code=status.HTTP_201_CREATED,
        )
