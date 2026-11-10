from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import ContactoForm, MayorInformacionForm


def contacto(request):
    """HU32: formulario de contacto general."""
    form = ContactoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if request.user.is_authenticated:
            obj.usuario = request.user
            if not obj.nombre:
                obj.nombre = request.user.get_full_name() or request.user.username
            if not obj.email:
                obj.email = request.user.email
        obj.save()
        messages.success(request, "Tu mensaje fue enviado. Te responderemos pronto.")
        return redirect("soporte:contacto")
    return render(request, "soporte/contacto.html", {"form": form})


def mayor_informacion(request):
    """HU33: el visitante deja sus datos para recibir información."""
    form = MayorInformacionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.asunto = "Solicitud de información"
        obj.mensaje = ""
        if request.user.is_authenticated:
            obj.usuario = request.user
        obj.save()
        messages.success(request, "¡Gracias! Nos pondremos en contacto contigo pronto.")
        return redirect("soporte:mayor_informacion")
    return render(request, "soporte/mayor_informacion.html", {"form": form})


def ayuda(request):
    """HU34: página de ayuda con secciones de uso del sistema."""
    return render(request, "soporte/ayuda.html")
