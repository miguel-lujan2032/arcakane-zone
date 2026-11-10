from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin

from .models import Rol, Usuario


@admin.register(Rol)
class RolAdmin(ModelAdmin):
    list_display = ["nombre", "activo"]
    list_filter = ["activo"]
    search_fields = ["nombre"]


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin, ModelAdmin):
    list_display = ["username", "email", "first_name", "last_name", "rol", "is_staff", "is_active"]
    list_filter = ["rol", "is_staff", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]
    fieldsets = UserAdmin.fieldsets + (
        ("Información adicional", {"fields": ("rol", "telefono", "direccion", "foto")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Información adicional", {"fields": ("rol", "telefono", "direccion")}),
    )
