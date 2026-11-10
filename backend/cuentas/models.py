from django.contrib.auth.models import AbstractUser
from django.db import models


class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    rol = models.ForeignKey(
        Rol,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarios",
    )
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    foto = models.ImageField(upload_to="usuarios/", null=True, blank=True)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def es_administrador(self) -> bool:
        return self.is_staff or (self.rol and self.rol.nombre.lower() == "administrador")

    @property
    def es_cliente(self) -> bool:
        return self.rol is not None and self.rol.nombre.lower() == "cliente"
