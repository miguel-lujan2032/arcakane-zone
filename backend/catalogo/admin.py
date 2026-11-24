from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import (
    Categoria,
    ClasificacionEdad,
    Desarrolladora,
    Distribuidora,
    Genero,
    Idioma,
    OfertaVideojuego,
    Plataforma,
    Videojuego,
    VideojuegoCategoria,
    VideojuegoDesarrolladora,
    VideojuegoDistribuidora,
    VideojuegoGenero,
    VideojuegoIdioma,
)


@admin.register(Categoria)
class CategoriaAdmin(ModelAdmin):
    list_display = ["nombre", "activo"]
    list_filter = ["activo"]
    search_fields = ["nombre"]


@admin.register(Plataforma)
class PlataformaAdmin(ModelAdmin):
    list_display = ["nombre", "activo"]
    list_filter = ["activo"]
    search_fields = ["nombre"]


@admin.register(Genero)
class GeneroAdmin(ModelAdmin):
    list_display = ["nombre", "activo"]
    list_filter = ["activo"]
    search_fields = ["nombre"]


@admin.register(Desarrolladora)
class DesarrolladoraAdmin(ModelAdmin):
    list_display = ["nombre", "codigo", "activo"]
    list_filter = ["activo"]
    search_fields = ["nombre", "codigo"]


@admin.register(Distribuidora)
class DistribuidoraAdmin(ModelAdmin):
    list_display = ["nombre", "codigo", "activo"]
    list_filter = ["activo"]
    search_fields = ["nombre", "codigo"]


@admin.register(ClasificacionEdad)
class ClasificacionEdadAdmin(ModelAdmin):
    list_display = ["nombre", "codigo", "orden"]
    ordering = ["orden", "codigo"]
    search_fields = ["nombre", "codigo"]


@admin.register(Idioma)
class IdiomaAdmin(ModelAdmin):
    list_display = ["nombre", "codigo"]
    search_fields = ["nombre", "codigo"]


class OfertaVideojuegoInline(TabularInline):
    model = OfertaVideojuego
    extra = 0
    fields = ["plataforma", "sku", "precio_vigente", "stock", "estado_publicacion"]


class VideojuegoCategoriaInline(TabularInline):
    """Asigna categorías del catálogo a un videojuego (tabla puente explícita)."""

    model = VideojuegoCategoria
    extra = 0
    fields = ["categoria"]


class VideojuegoGeneroInline(TabularInline):
    """Asigna géneros del catálogo a un videojuego (tabla puente explícita)."""

    model = VideojuegoGenero
    extra = 0
    fields = ["genero"]


class VideojuegoDesarrolladoraInline(TabularInline):
    """Asigna desarrolladoras del catálogo a un videojuego (AZ-S1-20)."""

    model = VideojuegoDesarrolladora
    extra = 0
    fields = ["desarrolladora"]


class VideojuegoDistribuidoraInline(TabularInline):
    """Asigna distribuidoras del catálogo a un videojuego (AZ-S1-20)."""

    model = VideojuegoDistribuidora
    extra = 0
    fields = ["distribuidora"]


class VideojuegoIdiomaInline(TabularInline):
    """Asigna idiomas y su tipo de presencia a un videojuego (AZ-S1-20)."""

    model = VideojuegoIdioma
    extra = 0
    fields = ["idioma", "tipo"]


@admin.register(Videojuego)
class VideojuegoAdmin(ModelAdmin):
    list_display = [
        "titulo",
        "clasificacion_edad",
        "categorias_lista",
        "generos_lista",
        "activo",
        "creado_en",
    ]
    list_filter = [
        "activo",
        "clasificacion_edad",
        "categorias",
        "generos",
        "desarrolladoras",
        "distribuidoras",
    ]
    search_fields = ["titulo", "descripcion"]
    date_hierarchy = "creado_en"
    inlines = [
        OfertaVideojuegoInline,
        VideojuegoCategoriaInline,
        VideojuegoGeneroInline,
        VideojuegoDesarrolladoraInline,
        VideojuegoDistribuidoraInline,
        VideojuegoIdiomaInline,
    ]

    def get_queryset(self, request):
        # Evita una consulta por fila al pintar las columnas M2M.
        return (
            super()
            .get_queryset(request)
            .select_related("clasificacion_edad")
            .prefetch_related(
                "categorias",
                "generos",
                "desarrolladoras",
                "distribuidoras",
                "idiomas",
            )
        )

    @admin.display(description="Categorías")
    def categorias_lista(self, obj):
        return ", ".join(categoria.nombre for categoria in obj.categorias.all())

    @admin.display(description="Géneros")
    def generos_lista(self, obj):
        return ", ".join(genero.nombre for genero in obj.generos.all())


@admin.register(OfertaVideojuego)
class OfertaVideojuegoAdmin(ModelAdmin):
    list_display = [
        "videojuego",
        "plataforma",
        "sku",
        "precio_vigente",
        "stock",
        "estado_publicacion",
    ]
    list_filter = [
        "estado_publicacion",
        "plataforma",
        "videojuego__categorias",
        "videojuego__generos",
    ]
    search_fields = ["sku", "videojuego__titulo"]
    list_editable = ["precio_vigente", "stock", "estado_publicacion"]
