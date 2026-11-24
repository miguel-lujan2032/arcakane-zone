"""
Pruebas de la normalización de roles de usuario (AZ-S1-18).

Cubre: unicidad de asignación y de código, integridad referencial, políticas
on_delete, cardinalidad usuario↔rol, propiedades de negocio con varios roles y
frontera con permisos técnicos de Django.
"""
import pytest
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError

from cuentas.models import Rol, Usuario, UsuarioRol


# ── Código de rol ────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_codigo_rol_unico():
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Rol.objects.create(codigo="cliente", nombre="Otro cliente")


# ── Unicidad de asignación ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_asignacion_duplicada_rechazada(usuario_cliente, rol_cliente):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            UsuarioRol.objects.create(usuario=usuario_cliente, rol=rol_cliente)


# ── Integridad referencial (FK inexistente) ──────────────────────────────────


@pytest.mark.django_db
def test_asignacion_rechaza_usuario_inexistente(rol_cliente):
    # SQLite difiere la comprobación de FKs; se fuerza con check_constraints().
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            UsuarioRol.objects.create(usuario_id=999999, rol=rol_cliente)
            connection.check_constraints()


@pytest.mark.django_db
def test_asignacion_rechaza_rol_inexistente(usuario_cliente):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            UsuarioRol.objects.create(usuario=usuario_cliente, rol_id=999999)
            connection.check_constraints()


# ── on_delete ────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_borrar_usuario_elimina_sus_asignaciones(usuario_cliente, rol_cliente, rol_admin):
    usuario_cliente.roles.add(rol_admin)
    pk = usuario_cliente.pk
    assert UsuarioRol.objects.filter(usuario_id=pk).count() == 2

    usuario_cliente.delete()

    assert UsuarioRol.objects.filter(usuario_id=pk).count() == 0


@pytest.mark.django_db
def test_borrar_rol_en_uso_bloqueado_por_protect(usuario_cliente, rol_cliente):
    with pytest.raises(ProtectedError):
        rol_cliente.delete()
    assert Rol.objects.filter(pk=rol_cliente.pk).exists()
    assert UsuarioRol.objects.filter(usuario=usuario_cliente, rol=rol_cliente).exists()


# ── Cardinalidad ─────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_usuario_con_cero_roles(db):
    u = Usuario.objects.create_user(username="sin_rol", password="x")
    assert u.roles.count() == 0
    assert not u.es_cliente
    assert not u.es_administrador


@pytest.mark.django_db
def test_usuario_con_un_rol(usuario_cliente, rol_cliente):
    assert usuario_cliente.roles.count() == 1
    assert usuario_cliente.roles.filter(pk=rol_cliente.pk).exists()


@pytest.mark.django_db
def test_usuario_con_varios_roles(usuario_cliente, rol_cliente, rol_admin):
    usuario_cliente.roles.add(rol_admin)
    codigos = set(usuario_cliente.roles.values_list("codigo", flat=True))
    assert codigos == {"cliente", "administrador"}
    assert usuario_cliente.roles.count() == 2


@pytest.mark.django_db
def test_rol_con_varios_usuarios(rol_cliente):
    u1 = Usuario.objects.create_user(username="c1", password="x")
    u2 = Usuario.objects.create_user(username="c2", password="x")
    u1.roles.add(rol_cliente)
    u2.roles.add(rol_cliente)
    assert rol_cliente.usuarios.count() >= 2
    assert set(rol_cliente.usuarios.filter(username__in=["c1", "c2"]).values_list("username", flat=True)) == {"c1", "c2"}


# ── Propiedades de negocio con varios roles ──────────────────────────────────


@pytest.mark.django_db
def test_es_cliente_con_varios_roles(usuario_cliente, rol_admin):
    usuario_cliente.roles.add(rol_admin)
    assert usuario_cliente.es_cliente is True
    assert usuario_cliente.es_administrador is True  # tiene rol administrador


@pytest.mark.django_db
def test_es_administrador_por_rol_sin_is_staff(db, rol_admin):
    u = Usuario.objects.create_user(username="adm_negocio", password="x")
    u.roles.add(rol_admin)
    assert u.is_staff is False
    assert u.es_administrador is True


@pytest.mark.django_db
def test_es_administrador_por_is_staff_sin_rol_admin(db, rol_cliente):
    u = Usuario.objects.create_user(username="staff_sin_rol_adm", password="x", is_staff=True)
    u.roles.add(rol_cliente)
    assert u.es_administrador is True  # compatibilidad transitoria con is_staff
    assert u.es_cliente is True


@pytest.mark.django_db
def test_es_cliente_falso_si_no_posee_rol(db, rol_admin):
    u = Usuario.objects.create_user(username="solo_admin", password="x")
    u.roles.add(rol_admin)
    assert u.es_cliente is False
    assert u.es_administrador is True


# ── Frontera con permisos técnicos de Django ─────────────────────────────────


@pytest.mark.django_db
def test_is_staff_sin_rol_de_negocio_no_crea_asignacion(db):
    u = Usuario.objects.create_user(username="staff_puro", password="x", is_staff=True)
    assert u.roles.count() == 0
    assert u.es_administrador is True  # por is_staff
    assert UsuarioRol.objects.filter(usuario=u).count() == 0


@pytest.mark.django_db
def test_superuser_sin_rol_de_negocio_no_crea_asignacion(db):
    u = Usuario.objects.create_superuser(
        username="super", password="x", email="s@example.com"
    )
    assert u.is_superuser is True
    assert u.roles.count() == 0
    assert UsuarioRol.objects.filter(usuario=u).count() == 0


@pytest.mark.django_db
def test_asignar_rol_administrador_no_otorga_is_staff_ni_permisos(db, rol_admin):
    u = Usuario.objects.create_user(username="adm_rol", password="x")
    u.roles.add(rol_admin)
    u.refresh_from_db()
    assert u.is_staff is False
    assert u.is_superuser is False
    assert not u.user_permissions.exists()
    assert not u.groups.exists()
    assert u.es_administrador is True  # rol de negocio, sin privilegios técnicos
