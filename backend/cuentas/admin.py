from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from unfold.admin import ModelAdmin, TabularInline

from .models import Rol, Usuario, UsuarioRol


@admin.register(Rol)
class RolAdmin(ModelAdmin):
    list_display = ["codigo", "nombre", "activo"]
    list_filter = ["activo"]
    search_fields = ["codigo", "nombre"]


class UsuarioRolInline(TabularInline):
    model = UsuarioRol
    extra = 0
    autocomplete_fields = ("rol",)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin, ModelAdmin):
    list_display = ["username", "email", "first_name", "last_name", "roles_list", "is_staff", "is_active"]
    list_filter = ["is_staff", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name"]
    inlines = [UsuarioRolInline]
    fieldsets = UserAdmin.fieldsets + (
        ("Información adicional", {"fields": ("telefono", "direccion", "foto")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Información adicional", {"fields": ("telefono", "direccion")}),
    )

    @admin.display(description="Roles")
    def roles_list(self, obj):
        return ", ".join(r.nombre for r in obj.roles.all()) or "—"
