from django.shortcuts import get_object_or_404, render

from .models import Categoria, Genero, OfertaVideojuego, Plataforma, Videojuego


def lista_videojuegos(request):
    ofertas = (
        OfertaVideojuego.objects.publicadas()
        .filter(videojuego__activo=True)
        .select_related("videojuego", "plataforma", "videojuego__categoria", "videojuego__genero")
    )
    categorias = Categoria.objects.filter(activo=True)
    plataformas = Plataforma.objects.filter(activo=True)
    generos = Genero.objects.filter(activo=True)

    # Filtros opcionales
    categoria_id = request.GET.get("categoria")
    plataforma_id = request.GET.get("plataforma")
    genero_id = request.GET.get("genero")
    busqueda = request.GET.get("q", "").strip()

    if categoria_id:
        ofertas = ofertas.filter(videojuego__categoria_id=categoria_id)
    if plataforma_id:
        ofertas = ofertas.filter(plataforma_id=plataforma_id)
    if genero_id:
        ofertas = ofertas.filter(videojuego__genero_id=genero_id)
    if busqueda:
        ofertas = ofertas.filter(videojuego__titulo__icontains=busqueda)

    contexto = {
        "ofertas": ofertas,
        "categorias": categorias,
        "plataformas": plataformas,
        "generos": generos,
    }
    return render(request, "catalogo/lista.html", contexto)


def detalle_videojuego(request, pk):
    videojuego = get_object_or_404(Videojuego, pk=pk, activo=True)
    ofertas = (
        videojuego.ofertas.publicadas()
        .select_related("plataforma")
        .order_by("precio_vigente")
    )
    return render(
        request,
        "catalogo/detalle.html",
        {"videojuego": videojuego, "ofertas": ofertas},
    )
