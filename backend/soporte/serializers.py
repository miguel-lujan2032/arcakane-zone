from rest_framework import serializers

from .models import Contacto


class ContactoSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = Contacto
        fields = [
            "id",
            "nombre",
            "email",
            "telefono",
            "asunto",
            "mensaje",
            "creado_en",
            "atendido",
        ]
        read_only_fields = ["id", "creado_en", "atendido"]

    def validate(self, attrs):
        request = self.context.get("request")
        usuario = getattr(request, "user", None)
        autenticado = usuario is not None and usuario.is_authenticated

        nombre = (attrs.get("nombre") or "").strip()
        email = (attrs.get("email") or "").strip()

        if autenticado:
            if not nombre:
                nombre = usuario.get_full_name() or usuario.username
            if not email:
                email = usuario.email

        if not nombre:
            raise serializers.ValidationError(
                {"nombre": "El nombre es obligatorio."}
            )
        if not email:
            raise serializers.ValidationError(
                {"email": "El correo electrónico es obligatorio."}
            )

        attrs["nombre"] = nombre
        attrs["email"] = email
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        usuario = getattr(request, "user", None)
        if usuario is not None and usuario.is_authenticated:
            validated_data["usuario"] = usuario
            if not validated_data.get("nombre"):
                validated_data["nombre"] = (
                    usuario.get_full_name() or usuario.username
                )
            if not validated_data.get("email"):
                validated_data["email"] = usuario.email
        return super().create(validated_data)


class ContactoAdminSerializer(ContactoSerializer):
    """Permite al staff marcar un contacto como atendido."""

    class Meta(ContactoSerializer.Meta):
        read_only_fields = ["id", "creado_en"]

    def validate(self, attrs):
        # En una actualización parcial solo se cambia ``atendido``; no se
        # deben reemplazar el nombre ni el correo del contacto original.
        if self.instance is not None:
            return attrs
        return super().validate(attrs)


class MayorInformacionSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    telefono = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default=""
    )

    def create(self, validated_data):
        request = self.context.get("request")
        usuario = getattr(request, "user", None)
        return Contacto.objects.create(
            nombre=validated_data["nombre"],
            email=validated_data["email"],
            telefono=validated_data.get("telefono", ""),
            asunto="Solicitud de información",
            mensaje="",
            usuario=usuario if usuario and usuario.is_authenticated else None,
        )
