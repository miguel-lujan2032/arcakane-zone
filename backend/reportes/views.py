from datetime import date

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.shortcuts import render

from catalogo.models import Categoria, Genero, OfertaVideojuego, Plataforma
from pagos.models import Venta
from pedidos.models import Pedido

UMBRAL_BAJO_STOCK = 5


def _ofertas_catalogo():
    """Ofertas del catálogo con su contexto de videojuego precargado."""
    return OfertaVideojuego.objects.select_related(
        "videojuego", "plataforma", "videojuego__categoria", "videojuego__genero"
    )


# ── HU28: Dashboard ─────────────────────────────────────────────────────────

@staff_member_required(login_url="login")
def dashboard(request):
    estados = (
        Pedido.objects.values("estado")
        .annotate(total=Count("id"))
        .order_by("estado")
    )
    conteo_estados = {e["estado"]: e["total"] for e in estados}

    total_ventas = Venta.objects.aggregate(suma=Sum("total"))["suma"] or 0
    num_pedidos_pagados = conteo_estados.get("pagado", 0)

    ofertas = _ofertas_catalogo()
    agotados = ofertas.publicadas().filter(stock=0, videojuego__activo=True)
    bajo_stock = ofertas.publicadas().filter(
        stock__gt=0, stock__lte=UMBRAL_BAJO_STOCK, videojuego__activo=True
    )

    contexto = {
        "total_ventas": total_ventas,
        "num_pedidos_pagados": num_pedidos_pagados,
        "conteo_pendiente": conteo_estados.get("pendiente", 0),
        "conteo_pagado": conteo_estados.get("pagado", 0),
        "conteo_cancelado": conteo_estados.get("cancelado", 0),
        "agotados": agotados,
        "bajo_stock": bajo_stock,
        "umbral": UMBRAL_BAJO_STOCK,
    }
    return render(request, "reportes/dashboard.html", contexto)


# ── HU29: Reporte de ventas ──────────────────────────────────────────────────

@staff_member_required(login_url="login")
def reporte_ventas(request):
    ventas = Venta.objects.select_related(
        "pedido__cliente"
    ).prefetch_related(
        "pedido__detalles"
    ).order_by("-registrada_en")

    fecha_desde = request.GET.get("desde", "")
    fecha_hasta = request.GET.get("hasta", "")

    if fecha_desde:
        try:
            ventas = ventas.filter(registrada_en__date__gte=date.fromisoformat(fecha_desde))
        except ValueError:
            fecha_desde = ""
    if fecha_hasta:
        try:
            ventas = ventas.filter(registrada_en__date__lte=date.fromisoformat(fecha_hasta))
        except ValueError:
            fecha_hasta = ""

    total_periodo = ventas.aggregate(suma=Sum("total"))["suma"] or 0

    contexto = {
        "ventas": ventas,
        "total_periodo": total_periodo,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
    }
    return render(request, "reportes/reporte_ventas.html", contexto)


# ── HU30: Reporte de inventario ──────────────────────────────────────────────

@staff_member_required(login_url="login")
def reporte_inventario(request):
    filtro = request.GET.get("filtro", "todos")

    ofertas = _ofertas_catalogo().order_by("videojuego__titulo", "plataforma__nombre")

    if filtro == "agotados":
        ofertas = ofertas.publicadas().filter(stock=0, videojuego__activo=True)
    elif filtro == "bajo_stock":
        ofertas = ofertas.publicadas().filter(
            stock__gt=0, stock__lte=UMBRAL_BAJO_STOCK, videojuego__activo=True
        )
    elif filtro == "disponibles":
        ofertas = ofertas.publicadas().filter(
            stock__gt=UMBRAL_BAJO_STOCK, videojuego__activo=True
        )
    elif filtro == "inactivas":
        ofertas = ofertas.exclude(estado_publicacion=OfertaVideojuego.EstadoPublicacion.PUBLICADO)

    contexto = {
        "ofertas": ofertas,
        "filtro": filtro,
        "umbral": UMBRAL_BAJO_STOCK,
        "total_agotados": _ofertas_catalogo()
        .publicadas()
        .filter(stock=0, videojuego__activo=True)
        .count(),
        "total_bajo_stock": _ofertas_catalogo()
        .publicadas()
        .filter(stock__gt=0, stock__lte=UMBRAL_BAJO_STOCK, videojuego__activo=True)
        .count(),
    }
    return render(request, "reportes/reporte_inventario.html", contexto)


# ── HU31: Reporte de videojuegos ─────────────────────────────────────────────

@staff_member_required(login_url="login")
def reporte_videojuegos(request):
    ofertas = _ofertas_catalogo().order_by("videojuego__titulo", "plataforma__nombre")

    categoria_id = request.GET.get("categoria", "")
    genero_id = request.GET.get("genero", "")
    plataforma_id = request.GET.get("plataforma", "")
    estado = request.GET.get("estado", "")
    disponibilidad = request.GET.get("disponibilidad", "")

    if categoria_id:
        ofertas = ofertas.filter(videojuego__categoria_id=categoria_id)
    if genero_id:
        ofertas = ofertas.filter(videojuego__genero_id=genero_id)
    if plataforma_id:
        ofertas = ofertas.filter(plataforma_id=plataforma_id)
    if estado == "activo":
        ofertas = ofertas.filter(videojuego__activo=True)
    elif estado == "inactivo":
        ofertas = ofertas.filter(videojuego__activo=False)
    if disponibilidad == "disponible":
        ofertas = ofertas.publicadas().filter(stock__gt=0, videojuego__activo=True)
    elif disponibilidad == "agotado":
        ofertas = ofertas.publicadas().filter(stock=0, videojuego__activo=True)

    contexto = {
        "ofertas": ofertas,
        "categorias": Categoria.objects.filter(activo=True).order_by("nombre"),
        "generos": Genero.objects.filter(activo=True).order_by("nombre"),
        "plataformas": Plataforma.objects.filter(activo=True).order_by("nombre"),
        "categoria_id": categoria_id,
        "genero_id": genero_id,
        "plataforma_id": plataforma_id,
        "estado": estado,
        "disponibilidad": disponibilidad,
    }
    return render(request, "reportes/reporte_videojuegos.html", contexto)
