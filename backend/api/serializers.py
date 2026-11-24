"""Serializadores de la API REST.

Los serializadores concentran la validación de entrada. Las reglas de negocio
que ya existen en ``pedidos.services`` y ``pagos.services`` se reutilizan tal
cual para no duplicar comportamiento entre las vistas HTML y la API.
"""
from django.contrib.auth import password_validation
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework import serializers

from catalogo.models import (
    Categoria,
    Genero,
    OfertaVideojuego,
    Plataforma,
    Videojuego,
    VideojuegoCategoria,
    VideojuegoGenero,
)
from cuentas.models import Rol, Usuario
from pagos.models import IntentoPago, Venta
from pedidos.models import DetallePedido, EstadoPedido, Pedido
from soporte.models import Contacto

from .password_reset import TokenResetInvalido, resolver_usuario


def _ordenados_por_nombre(gestor):
    """Ordena en Python para reutilizar el ``prefetch_related`` del viewset."""
    return sorted(gestor.all(), key=lambda objeto: objeto.nombre)


def _primero_por_nombre(gestor):
    objetos = _ordenados_por_nombre(gestor)
    return objetos[0] if objetos else None


def codigos_estado_pedido():
    """Códigos vigentes del catálogo de estados (mismo texto del contrato v1)."""
    return list(EstadoPedido.objects.values_list("codigo", flat=True))


class _PrimerRelacionadoField(serializers.Field):
    """Campo de compatibilidad: un único id, el primero por nombre.

    Sigue aceptando y devolviendo la forma histórica de ``categoria``,
    ``genero`` y ``rol`` aunque el modelo normalize la relación como M2M.
    """

    def __init__(self, queryset, related_name, **kwargs):
        self.queryset = queryset
        self.related_name = related_name
        super().__init__(**kwargs)

    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        primero = _primero_por_nombre(getattr(instance, self.related_name))
        return primero.pk if primero is not None else None

    def to_internal_value(self, data):
        try:
            return self.queryset.get(pk=data)
        except (TypeError, ValueError, ObjectDoesNotExist) as exc:
            raise serializers.ValidationError("Valor inválido.") from exc


class _RelacionadosField(serializers.Field):
    """Lista aditiva de ids, ordenada por nombre de forma determinista."""

    def __init__(self, queryset, related_name, **kwargs):
        self.queryset = queryset
        self.related_name = related_name
        super().__init__(**kwargs)

    def get_attribute(self, instance):
        return instance

    def to_representation(self, instance):
        return [objeto.pk for objeto in _ordenados_por_nombre(getattr(instance, self.related_name))]

    def to_internal_value(self, data):
        if not isinstance(data, (list, tuple)):
            raise serializers.ValidationError("Se espera una lista de identificadores.")
        objetos = []
        for valor in data:
            try:
                objeto = self.queryset.get(pk=valor)
            except (TypeError, ValueError, ObjectDoesNotExist) as exc:
                raise serializers.ValidationError("Valor inválido.") from exc
            if objeto not in objetos:
                objetos.append(objeto)
        return objetos


# ── Catálogo ─────────────────────────────────────────────────────────────────

class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion", "activo"]

    def validate_nombre(self, value):
        return value.strip()


class PlataformaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plataforma
        fields = ["id", "nombre", "descripcion", "activo"]

    def validate_nombre(self, value):
        return value.strip()


class GeneroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genero
        fields = ["id", "nombre", "descripcion", "activo"]

    def validate_nombre(self, value):
        return value.strip()


class OfertaResumenSerializer(serializers.ModelSerializer):
    """Representación breve de una oferta dentro del detalle de un título."""

    plataforma_nombre = serializers.CharField(source="plataforma.nombre", read_only=True)
    disponible = serializers.BooleanField(read_only=True)

    class Meta:
        model = OfertaVideojuego
        fields = [
            "id",
            "plataforma",
            "plataforma_nombre",
            "sku",
            "precio_vigente",
            "stock",
            "estado_publicacion",
            "disponible",
        ]


class OfertaVideojuegoSerializer(serializers.ModelSerializer):
    videojuego_titulo = serializers.CharField(source="videojuego.titulo", read_only=True)
    plataforma_nombre = serializers.CharField(source="plataforma.nombre", read_only=True)
    disponible = serializers.BooleanField(read_only=True)

    class Meta:
        model = OfertaVideojuego
        fields = [
            "id",
            "videojuego",
            "videojuego_titulo",
            "plataforma",
            "plataforma_nombre",
            "precio_vigente",
            "sku",
            "stock",
            "estado_publicacion",
            "disponible",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["creado_en", "actualizado_en"]
        # La unicidad se valida en ``validate`` con un mensaje de campo claro.
        validators = []

    def validate_precio_vigente(self, value):
        if value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return value

    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("El stock no puede ser negativo.")
        return value

    def validate_sku(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        videojuego = attrs.get("videojuego", getattr(self.instance, "videojuego", None))
        plataforma = attrs.get("plataforma", getattr(self.instance, "plataforma", None))
        sku = attrs.get("sku", getattr(self.instance, "sku", None))

        if sku:
            existentes_sku = OfertaVideojuego.objects.filter(sku__iexact=sku)
            if self.instance is not None:
                existentes_sku = existentes_sku.exclude(pk=self.instance.pk)
            if existentes_sku.exists():
                raise serializers.ValidationError(
                    {"sku": "Ya existe una oferta con ese SKU."}
                )

        if videojuego and plataforma:
            existentes = OfertaVideojuego.objects.filter(
                videojuego=videojuego, plataforma=plataforma
            )
            if self.instance is not None:
                existentes = existentes.exclude(pk=self.instance.pk)
            if existentes.exists():
                raise serializers.ValidationError(
                    {
                        "plataforma": (
                            "Ya existe una oferta para este videojuego en esa plataforma."
                        )
                    }
                )
        return attrs


class VideojuegoSerializer(serializers.ModelSerializer):
    # ``categoria``/``genero`` se conservan por compatibilidad; las listas
    # ``categorias``/``generos`` son la forma normalizada del contrato.
    categoria = _PrimerRelacionadoField(
        queryset=Categoria.objects, related_name="categorias", required=False
    )
    categoria_nombre = serializers.SerializerMethodField()
    categorias = _RelacionadosField(
        queryset=Categoria.objects, related_name="categorias", required=False
    )
    genero = _PrimerRelacionadoField(
        queryset=Genero.objects, related_name="generos", required=False
    )
    genero_nombre = serializers.SerializerMethodField()
    generos = _RelacionadosField(
        queryset=Genero.objects, related_name="generos", required=False
    )
    disponible = serializers.SerializerMethodField()
    ofertas = OfertaResumenSerializer(many=True, read_only=True)

    class Meta:
        model = Videojuego
        fields = [
            "id",
            "titulo",
            "descripcion",
            "portada",
            "fecha_lanzamiento",
            "categoria",
            "categoria_nombre",
            "categorias",
            "genero",
            "genero_nombre",
            "generos",
            "activo",
            "disponible",
            "ofertas",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["creado_en", "actualizado_en"]

    def validate_titulo(self, value):
        return value.strip()

    def to_internal_value(self, data):
        # Los errores de campo (p. ej. título vacío) impiden llegar a
        # ``validate``; se añaden aquí para no perder los errores históricos
        # de ``categoria``/``genero`` en la respuesta 400.
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError as exc:
            detalles = exc.detail
            if self.instance is None and isinstance(detalles, dict):
                if not data.get("categoria") and not data.get("categorias"):
                    detalles.setdefault("categoria", ["Este campo es obligatorio."])
                if not data.get("genero") and not data.get("generos"):
                    detalles.setdefault("genero", ["Este campo es obligatorio."])
            raise

    def validate(self, attrs):
        if self.instance is None:
            errores = {}
            if not attrs.get("categoria") and not attrs.get("categorias"):
                errores["categoria"] = ["Este campo es obligatorio."]
            if not attrs.get("genero") and not attrs.get("generos"):
                errores["genero"] = ["Este campo es obligatorio."]
            if errores:
                raise serializers.ValidationError(errores)

        categoria = attrs.pop("categoria", None)
        if categoria is not None and not attrs.get("categorias"):
            attrs["categorias"] = [categoria]
        genero = attrs.pop("genero", None)
        if genero is not None and not attrs.get("generos"):
            attrs["generos"] = [genero]
        return attrs

    def get_categoria_nombre(self, obj):
        primero = _primero_por_nombre(obj.categorias)
        return primero.nombre if primero is not None else None

    def get_genero_nombre(self, obj):
        primero = _primero_por_nombre(obj.generos)
        return primero.nombre if primero is not None else None

    def get_disponible(self, obj):
        # Calculado sobre las ofertas precargadas para evitar una consulta por
        # videojuego al serializar el listado.
        return any(oferta.disponible for oferta in obj.ofertas.all())

    @staticmethod
    def _sincronizar(modelo, campo, instancia, valores):
        if valores is None:
            return
        modelo.objects.filter(videojuego=instancia).exclude(**{f"{campo}__in": valores}).delete()
        for valor in valores:
            modelo.objects.get_or_create(videojuego=instancia, **{campo: valor})

    def create(self, validated_data):
        categorias = validated_data.pop("categorias", [])
        generos = validated_data.pop("generos", [])
        with transaction.atomic():
            instancia = super().create(validated_data)
            self._sincronizar(VideojuegoCategoria, "categoria", instancia, categorias)
            self._sincronizar(VideojuegoGenero, "genero", instancia, generos)
        return instancia

    def update(self, instance, validated_data):
        categorias = validated_data.pop("categorias", None)
        generos = validated_data.pop("generos", None)
        with transaction.atomic():
            instancia = super().update(instance, validated_data)
            self._sincronizar(VideojuegoCategoria, "categoria", instancia, categorias)
            self._sincronizar(VideojuegoGenero, "genero", instancia, generos)
        return instancia


class VideojuegoResumenSerializer(serializers.ModelSerializer):
    categoria = _PrimerRelacionadoField(
        queryset=Categoria.objects, related_name="categorias", read_only=True
    )
    categoria_nombre = serializers.SerializerMethodField()
    categorias = _RelacionadosField(
        queryset=Categoria.objects, related_name="categorias", read_only=True
    )
    genero = _PrimerRelacionadoField(
        queryset=Genero.objects, related_name="generos", read_only=True
    )
    genero_nombre = serializers.SerializerMethodField()
    generos = _RelacionadosField(
        queryset=Genero.objects, related_name="generos", read_only=True
    )

    class Meta:
        model = Videojuego
        fields = [
            "id",
            "titulo",
            "categoria",
            "categoria_nombre",
            "categorias",
            "genero",
            "genero_nombre",
            "generos",
            "activo",
        ]

    def get_categoria_nombre(self, obj):
        primero = _primero_por_nombre(obj.categorias)
        return primero.nombre if primero is not None else None

    def get_genero_nombre(self, obj):
        primero = _primero_por_nombre(obj.generos)
        return primero.nombre if primero is not None else None


# ── Carrito y pedidos ────────────────────────────────────────────────────────

class OfertaEnDetalleSerializer(serializers.ModelSerializer):
    """Datos comerciales actuales de la oferta referenciada por una línea."""

    videojuego = VideojuegoResumenSerializer(read_only=True)
    plataforma_nombre = serializers.CharField(source="plataforma.nombre", read_only=True)

    class Meta:
        model = OfertaVideojuego
        fields = [
            "id",
            "videojuego",
            "plataforma",
            "plataforma_nombre",
            "sku",
            "precio_vigente",
            "stock",
            "estado_publicacion",
        ]


class DetallePedidoSerializer(serializers.ModelSerializer):
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    oferta_detalle = serializers.SerializerMethodField()

    class Meta:
        model = DetallePedido
        fields = [
            "id",
            "oferta",
            "oferta_detalle",
            "cantidad",
            "precio_unitario",
            "titulo_snapshot",
            "plataforma_snapshot",
            "subtotal",
        ]
        read_only_fields = [
            "precio_unitario",
            "titulo_snapshot",
            "plataforma_snapshot",
        ]

    def get_oferta_detalle(self, obj):
        return OfertaEnDetalleSerializer(obj.oferta, context=self.context).data


class CarritoItemCreateSerializer(serializers.Serializer):
    oferta = serializers.PrimaryKeyRelatedField(queryset=OfertaVideojuego.objects.all())
    cantidad = serializers.IntegerField(min_value=1, default=1)


class CarritoItemUpdateSerializer(serializers.Serializer):
    cantidad = serializers.IntegerField(min_value=0)


class CarritoSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_items = serializers.SerializerMethodField()

    class Meta:
        model = Pedido
        fields = [
            "id",
            "estado",
            "total",
            "total_items",
            "detalles",
            "creado_en",
            "actualizado_en",
        ]

    def get_total_items(self, obj):
        return sum(detalle.cantidad for detalle in obj.detalles.all())


class PagoResumenSerializer(serializers.ModelSerializer):
    """Intento de pago con la forma JSON histórica (``monto`` = ``importe``)."""

    monto = serializers.DecimalField(
        source="importe", max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = IntentoPago
        fields = ["id", "monto", "estado", "referencia", "creado_en"]


class VentaResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venta
        fields = ["id", "total", "registrada_en"]


class PedidoSerializer(serializers.ModelSerializer):
    cliente = serializers.IntegerField(source="cliente_id", read_only=True)
    cliente_username = serializers.CharField(source="cliente.username", read_only=True)
    detalles = DetallePedidoSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    puede_cancelar = serializers.BooleanField(read_only=True)
    pago = serializers.SerializerMethodField()
    intentos_pago = PagoResumenSerializer(many=True, read_only=True)
    venta = serializers.SerializerMethodField()

    class Meta:
        model = Pedido
        fields = [
            "id",
            "cliente",
            "cliente_username",
            "estado",
            "total",
            "puede_cancelar",
            "detalles",
            "pago",
            "intentos_pago",
            "venta",
            "creado_en",
            "actualizado_en",
        ]

    def get_pago(self, obj):
        # El viewset precarga el intento aprobado; fuera de él se usa la
        # propiedad de compatibilidad ``Pedido.pago``.
        aprobados = getattr(obj, "_intentos_aprobados", None)
        if aprobados is not None:
            pago = aprobados[0] if aprobados else None
        else:
            pago = getattr(obj, "pago", None)
        if pago is None:
            return None
        return PagoResumenSerializer(pago, context=self.context).data

    def get_venta(self, obj):
        venta = getattr(obj, "venta", None)
        if venta is None:
            return None
        return VentaResumenSerializer(venta, context=self.context).data


class PedidoEstadoSerializer(serializers.Serializer):
    """Transición de estado permitida a través de ``PATCH /pedidos/{id}/``."""

    estado = serializers.CharField()

    def validate_estado(self, value):
        if value not in codigos_estado_pedido():
            raise serializers.ValidationError(f'"{value}" no es una opción válida.')
        if value != "cancelado":
            raise serializers.ValidationError(
                "La única transición permitida por este endpoint es 'cancelado'."
            )
        return value


# ── Pagos y ventas ───────────────────────────────────────────────────────────

class PagoSerializer(serializers.ModelSerializer):
    pedido = serializers.IntegerField(source="pedido_id", read_only=True)
    cliente = serializers.CharField(source="pedido.cliente.username", read_only=True)
    monto = serializers.DecimalField(
        source="importe", max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = IntentoPago
        fields = [
            "id",
            "pedido",
            "cliente",
            "monto",
            "estado",
            "referencia",
            "creado_en",
        ]


class PagoCreateSerializer(serializers.Serializer):
    pedido = serializers.PrimaryKeyRelatedField(queryset=Pedido.objects.all())


class VentaSerializer(serializers.ModelSerializer):
    pedido = serializers.IntegerField(source="pedido_id", read_only=True)
    cliente = serializers.CharField(source="pedido.cliente.username", read_only=True)
    detalles = DetallePedidoSerializer(source="pedido.detalles", many=True, read_only=True)

    class Meta:
        model = Venta
        fields = [
            "id",
            "pedido",
            "cliente",
            "total",
            "detalles",
            "registrada_en",
        ]


# ── Cuentas ──────────────────────────────────────────────────────────────────

class RolSerializer(serializers.ModelSerializer):
    """``nombre`` conserva el texto histórico del contrato v1.

    La semilla puede tener etiquetas visibles con otra capitalización; el
    código estable es el que la API expuso siempre como ``nombre``.
    """

    nombre = serializers.SerializerMethodField()

    class Meta:
        model = Rol
        fields = ["id", "codigo", "nombre", "descripcion", "activo"]

    def get_nombre(self, obj):
        return obj.codigo or obj.nombre


class UsuarioSerializer(serializers.ModelSerializer):
    # ``rol``/``rol_nombre`` son los campos históricos: exponen el primero por
    # nombre y el código estable, respectivamente. ``roles`` es la lista nueva.
    rol = _PrimerRelacionadoField(
        queryset=Rol.objects, related_name="roles", read_only=True
    )
    rol_nombre = serializers.SerializerMethodField()
    roles = _RelacionadosField(
        queryset=Rol.objects, related_name="roles", read_only=True
    )

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "telefono",
            "direccion",
            "rol",
            "rol_nombre",
            "roles",
            "is_active",
            "is_staff",
            "date_joined",
        ]
        read_only_fields = fields

    def get_rol_nombre(self, obj):
        primero = _primero_por_nombre(obj.roles)
        return primero.codigo if primero is not None else None


class PerfilSerializer(serializers.ModelSerializer):
    rol = _PrimerRelacionadoField(
        queryset=Rol.objects, related_name="roles", read_only=True
    )
    rol_nombre = serializers.SerializerMethodField()
    roles = _RelacionadosField(
        queryset=Rol.objects, related_name="roles", read_only=True
    )

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "telefono",
            "direccion",
            "foto",
            "rol",
            "rol_nombre",
            "roles",
            "date_joined",
        ]
        read_only_fields = ["id", "username", "rol", "rol_nombre", "roles", "date_joined"]

    def get_rol_nombre(self, obj):
        primero = _primero_por_nombre(obj.roles)
        return primero.codigo if primero is not None else None

    def validate_email(self, value):
        if not value:
            return value
        usuarios = Usuario.objects.filter(email__iexact=value).exclude(pk=self.instance.pk)
        if usuarios.exists():
            raise serializers.ValidationError(
                "Ya existe una cuenta con ese correo electrónico."
            )
        return value


class RegistroSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = Usuario
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "telefono",
            "direccion",
            "password",
            "password_confirm",
        ]
        extra_kwargs = {
            # La unicidad se valida con un mensaje propio en validate_username.
            "username": {"validators": []},
        }

    def validate_username(self, value):
        if Usuario.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese nombre.")
        return value

    def validate_email(self, value):
        if Usuario.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "Ya existe una cuenta con ese correo electrónico."
            )
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Las contraseñas no coinciden."}
            )
        usuario = Usuario(
            username=attrs.get("username"),
            email=attrs.get("email"),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            password_validation.validate_password(attrs["password"], usuario)
        except Exception as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        rol_cliente, _ = Rol.objects.get_or_create(
            codigo="cliente", defaults={"nombre": "cliente"}
        )
        usuario = Usuario(**validated_data)
        usuario.set_password(password)
        usuario.save()
        usuario.roles.add(rol_cliente)
        return usuario


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class CambioPasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("La contraseña actual es incorrecta.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Las contraseñas nuevas no coinciden."}
            )
        try:
            password_validation.validate_password(
                attrs["new_password"], self.context["request"].user
            )
        except Exception as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    token = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        uid, token = attrs.get("uid"), attrs.get("token")
        if not uid or not token:
            raise TokenResetInvalido()
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Las contraseñas nuevas no coinciden."}
            )
        usuario = resolver_usuario(uid, token)
        try:
            password_validation.validate_password(attrs["new_password"], usuario)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}) from exc
        attrs["usuario"] = usuario
        return attrs


# ── Soporte ──────────────────────────────────────────────────────────────────

class ContactoSerializer(serializers.ModelSerializer):
    # Los usuarios autenticados pueden omitir nombre/email: se completan con
    # los datos de su cuenta. Para visitantes se validan en ``validate``.
    nombre = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    asunto = serializers.CharField(max_length=200, required=False, allow_blank=True)

    class Meta:
        model = Contacto
        fields = [
            "id",
            "nombre",
            "email",
            "telefono",
            "asunto",
            "mensaje",
            "usuario",
            "creado_en",
            "atendido",
        ]
        read_only_fields = ["id", "usuario", "creado_en"]

    def validate(self, attrs):
        request = self.context.get("request")
        usuario = getattr(request, "user", None)
        autenticado = bool(usuario and usuario.is_authenticated)

        nombre = attrs.get("nombre", getattr(self.instance, "nombre", ""))
        email = attrs.get("email", getattr(self.instance, "email", ""))
        asunto = attrs.get("asunto", getattr(self.instance, "asunto", ""))

        errores = {}
        if not nombre:
            errores["nombre"] = "El nombre es obligatorio."
        if not email:
            errores["email"] = "El correo electrónico es obligatorio."
        if not asunto:
            errores["asunto"] = "El asunto es obligatorio."
        if errores and not autenticado:
            raise serializers.ValidationError(errores)
        return attrs


class SolicitudInformacionSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
