from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import CambioPasswordForm, PerfilForm, RegistroForm


def registro(request):
    if request.user.is_authenticated:
        return redirect("/")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, "¡Cuenta creada exitosamente!")
        return redirect("/")
    return render(request, "cuentas/registro.html", {"form": form})


@login_required
def perfil(request):
    """HU4: ver y editar datos personales del usuario autenticado."""
    form = PerfilForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Perfil actualizado correctamente.")
        return redirect("cuentas:perfil")
    return render(request, "cuentas/perfil.html", {"form": form})


@login_required
def cambiar_password(request):
    """HU3: cambio de contraseña para usuario autenticado."""
    form = CambioPasswordForm(user=request.user, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        update_session_auth_hash(request, form.user)
        messages.success(request, "Contraseña actualizada correctamente.")
        return redirect("cuentas:perfil")
    return render(request, "cuentas/cambiar_password.html", {"form": form})
