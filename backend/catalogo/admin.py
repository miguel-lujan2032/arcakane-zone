from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline

from .models import Categoria, Genero, OfertaVideojuego, Plataforma, Videojuego


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


class OfertaVideojuegoInline(TabularInline):
    model = OfertaVideojuego
    extra = 0
    fields = ["plataforma", "sku", "precio_vigente", "stock", "estado_publicacion"]


@admin.register(Videojuego)
class VideojuegoAdmin(ModelAdmin):
    list_display = ["titulo", "categoria", "genero", "activo", "creado_en"]
    list_filter = ["activo", "categoria", "genero"]
    search_fields = ["titulo", "descripcion"]
    date_hierarchy = "creado_en"
    inlines = [OfertaVideojuegoInline]


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
    list_filter = ["estado_publicacion", "plataforma", "videojuego__categoria"]
    search_fields = ["sku", "videojuego__titulo"]
    list_editable = ["precio_vigente", "stock", "estado_publicacion"]
