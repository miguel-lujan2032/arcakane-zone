from rest_framework import serializers

from .models import Categoria, Genero, Plataforma, Videojuego


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion", "activo"]


class PlataformaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plataforma
        fields = ["id", "nombre", "descripcion", "activo"]


class GeneroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genero
        fields = ["id", "nombre", "descripcion", "activo"]


class VideojuegoResumenSerializer(serializers.ModelSerializer):
    disponible = serializers.BooleanField(read_only=True)

    class Meta:
        model = Videojuego
        fields = ["id", "titulo", "precio", "stock", "portada", "disponible"]


class VideojuegoSerializer(serializers.ModelSerializer):
    categoria = CategoriaSerializer(read_only=True)
    plataforma = PlataformaSerializer(read_only=True)
    genero = GeneroSerializer(read_only=True)

    categoria_id = serializers.PrimaryKeyRelatedField(
        source="categoria", queryset=Categoria.objects.all(), write_only=True
    )
    plataforma_id = serializers.PrimaryKeyRelatedField(
        source="plataforma", queryset=Plataforma.objects.all(), write_only=True
    )
    genero_id = serializers.PrimaryKeyRelatedField(
        source="genero", queryset=Genero.objects.all(), write_only=True
    )
    disponible = serializers.BooleanField(read_only=True)
    portada = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Videojuego
        fields = [
            "id",
            "titulo",
            "descripcion",
            "precio",
            "stock",
            "portada",
            "fecha_lanzamiento",
            "categoria",
            "categoria_id",
            "plataforma",
            "plataforma_id",
            "genero",
            "genero_id",
            "activo",
            "disponible",
            "creado_en",
            "actualizado_en",
        ]
        read_only_fields = ["id", "creado_en", "actualizado_en"]

    def validate_precio(self, value):
        if value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return value
