"""
Pruebas de las migraciones de normalización de roles (AZ-S1-18).

Cubre: migración desde el esquema anterior con datos (usuarios con y sin rol),
nombre sin mapeo aborta con mensaje claro, y reversión con datos incluyendo el
caso de varios roles (restaura administrador si existe, si no el de menor PK de
asignación).
"""
import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from cuentas.models import Rol, Usuario, UsuarioRol


CUENTAS_ANTES = [("cuentas", "0001_initial")]
CUENTAS_DESPUES = [("cuentas", "0007_usuario_roles_m2m")]


def _all_leaf_nodes(executor):
    leaves = set(executor.loader.graph.leaf_nodes())
    return leaves


def _targets_with_cuentas(executor, cuentas_node):
    leaves = _all_leaf_nodes(executor)
    leaves = {n for n in leaves if n[0] != "cuentas"}
    leaves.add(cuentas_node)
    return list(leaves)


def _migrate(targets=None):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    if targets is None:
        targets = executor.loader.graph.leaf_nodes()
    executor.migrate(targets)
    return executor


def _migrate_cuentas(node):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    targets = _targets_with_cuentas(executor, node)
    executor.migrate(targets)
    return executor


def _apps_at_cuentas(node):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    targets = _targets_with_cuentas(executor, node)
    state = executor.loader.project_state(targets)
    return state.apps


@pytest.mark.django_db(transaction=True)
def test_migracion_desde_esquema_anterior_con_datos():
    # Lleva cuentas al esquema anterior (FK directa) manteniendo el resto al día.
    _migrate_cuentas(CUENTAS_ANTES[0])
    apps = _apps_at_cuentas(CUENTAS_ANTES[0])
    RolViejo = apps.get_model("cuentas", "Rol")
    UsuarioViejo = apps.get_model("cuentas", "Usuario")

    # Limpia roles que puedan existir (p. ej. sembrados por fixtures autouse).
    UsuarioViejo.objects.update(rol=None)
    RolViejo.objects.all().delete()

    rol_cliente = RolViejo.objects.create(nombre="cliente", activo=True)
    rol_admin = RolViejo.objects.create(nombre="administrador", activo=True)
    u_con_cliente = UsuarioViejo.objects.create_user(
        username="u_cli", password="x", rol=rol_cliente
    )
    u_con_admin = UsuarioViejo.objects.create_user(
        username="u_adm", password="x", rol=rol_admin
    )
    u_sin_rol = UsuarioViejo.objects.create_user(username="u_none", password="x")

    # Aplica la cadena completa de cuentas.
    _migrate_cuentas(CUENTAS_DESPUES[0])

    u_con_cliente = Usuario.objects.get(pk=u_con_cliente.pk)
    u_con_admin = Usuario.objects.get(pk=u_con_admin.pk)
    u_sin_rol = Usuario.objects.get(pk=u_sin_rol.pk)

    assert set(u_con_cliente.roles.values_list("codigo", flat=True)) == {"cliente"}
    assert set(u_con_admin.roles.values_list("codigo", flat=True)) == {"administrador"}
    assert u_sin_rol.roles.count() == 0

    assert Rol.objects.filter(codigo="cliente").exists()
    assert Rol.objects.filter(codigo="administrador").exists()

    # Vuelve al estado final para no interferir con otras pruebas.
    _migrate()


@pytest.mark.django_db(transaction=True)
def test_migracion_nombre_sin_mapeo_aborta_con_mensaje_claro():
    _migrate_cuentas(CUENTAS_ANTES[0])
    apps = _apps_at_cuentas(CUENTAS_ANTES[0])
    RolViejo = apps.get_model("cuentas", "Rol")
    UsuarioViejo = apps.get_model("cuentas", "Usuario")

    UsuarioViejo.objects.update(rol=None)
    RolViejo.objects.all().delete()
    RolViejo.objects.create(nombre="moderador", activo=True)

    with pytest.raises(RuntimeError) as excinfo:
        # 0003 realiza el mapeo y debe abortar.
        _migrate_cuentas(("cuentas", "0003_poblar_codigo_roles"))

    mensaje = str(excinfo.value)
    assert "cuentas_rol" in mensaje
    assert "nombre" in mensaje
    assert "moderador" in mensaje
    assert "1 fila" in mensaje

    # Limpia el dato inválido y recupera el estado final.
    apps = _apps_at_cuentas(("cuentas", "0002_rol_codigo_nullable"))
    apps.get_model("cuentas", "Rol").objects.filter(nombre="moderador").delete()
    _migrate()


@pytest.mark.django_db(transaction=True)
def test_reversion_completa_con_datos_hasta_0001():
    _migrate_cuentas(CUENTAS_ANTES[0])
    apps = _apps_at_cuentas(CUENTAS_ANTES[0])
    RolViejo = apps.get_model("cuentas", "Rol")
    UsuarioViejo = apps.get_model("cuentas", "Usuario")

    UsuarioViejo.objects.update(rol=None)
    RolViejo.objects.all().delete()

    rol_cliente = RolViejo.objects.create(nombre="cliente", activo=True)
    rol_admin = RolViejo.objects.create(nombre="administrador", activo=True)
    u_cli = UsuarioViejo.objects.create_user(username="rv_cli", password="x", rol=rol_cliente)
    u_none = UsuarioViejo.objects.create_user(username="rv_none", password="x")

    _migrate_cuentas(CUENTAS_DESPUES[0])
    assert set(Usuario.objects.get(pk=u_cli.pk).roles.values_list("codigo", flat=True)) == {"cliente"}

    # Revierte completamente a 0001.
    _migrate_cuentas(CUENTAS_ANTES[0])
    apps_viejo = _apps_at_cuentas(CUENTAS_ANTES[0])
    UsuarioViejo = apps_viejo.get_model("cuentas", "Usuario")
    RolViejo = apps_viejo.get_model("cuentas", "Rol")

    u_cli_v = UsuarioViejo.objects.get(pk=u_cli.pk)
    u_none_v = UsuarioViejo.objects.get(pk=u_none.pk)
    rol_cliente_v = RolViejo.objects.get(nombre="cliente")
    assert u_cli_v.rol_id == rol_cliente_v.pk
    assert u_none_v.rol_id is None

    _migrate()


@pytest.mark.django_db(transaction=True)
def test_reversion_con_varios_roles_restaurar_admin_o_menor_pk():
    """Al revertir, si hay varios roles se restaura administrador si existe; si no, el de menor PK de asignación."""
    _migrate_cuentas(CUENTAS_ANTES[0])
    apps = _apps_at_cuentas(CUENTAS_ANTES[0])
    RolViejo = apps.get_model("cuentas", "Rol")
    UsuarioViejo = apps.get_model("cuentas", "Usuario")

    UsuarioViejo.objects.update(rol=None)
    RolViejo.objects.all().delete()

    rol_cliente = RolViejo.objects.create(nombre="cliente", activo=True)
    rol_admin = RolViejo.objects.create(nombre="administrador", activo=True)
    u_con_ambos = UsuarioViejo.objects.create_user(
        username="multi1", password="x", rol=rol_cliente
    )
    u_solo_cliente = UsuarioViejo.objects.create_user(
        username="multi2", password="x", rol=rol_cliente
    )

    _migrate_cuentas(CUENTAS_DESPUES[0])

    # Caso 1: usuario con cliente y administrador -> al revertir debe quedar administrador.
    u1 = Usuario.objects.get(pk=u_con_ambos.pk)
    u1.roles.add(Rol.objects.get(codigo="administrador"))

    # Caso 2: usuario con solo cliente (una asignación) -> queda cliente.
    # (ya está así)

    _migrate_cuentas(CUENTAS_ANTES[0])
    apps_viejo = _apps_at_cuentas(CUENTAS_ANTES[0])
    UsuarioViejo = apps_viejo.get_model("cuentas", "Usuario")
    RolViejo = apps_viejo.get_model("cuentas", "Rol")

    rol_admin_v = RolViejo.objects.get(nombre="administrador")
    rol_cliente_v = RolViejo.objects.get(nombre="cliente")

    assert UsuarioViejo.objects.get(pk=u_con_ambos.pk).rol_id == rol_admin_v.pk
    assert UsuarioViejo.objects.get(pk=u_solo_cliente.pk).rol_id == rol_cliente_v.pk

    _migrate()


@pytest.mark.django_db(transaction=True)
def test_reversion_sin_admin_restaura_menor_pk_asignacion():
    """Sin rol administrador entre las asignaciones, se restaura la de menor PK."""
    _migrate_cuentas(CUENTAS_ANTES[0])
    apps = _apps_at_cuentas(CUENTAS_ANTES[0])
    RolViejo = apps.get_model("cuentas", "Rol")
    UsuarioViejo = apps.get_model("cuentas", "Usuario")

    UsuarioViejo.objects.update(rol=None)
    RolViejo.objects.all().delete()

    rol_cliente = RolViejo.objects.create(nombre="cliente", activo=True)
    u = UsuarioViejo.objects.create_user(username="multi_no_admin", password="x", rol=rol_cliente)

    _migrate_cuentas(CUENTAS_DESPUES[0])

    # En el esquema final se añade otro rol (no administrador). La asignación
    # existente (cliente) tiene menor PK que la nueva.
    rol_extra = Rol.objects.create(codigo="moderador", nombre="Moderador")
    usuario = Usuario.objects.get(pk=u.pk)
    usuario.roles.add(rol_extra)
    assert usuario.roles.count() == 2
    assert not usuario.roles.filter(codigo="administrador").exists()

    _migrate_cuentas(CUENTAS_ANTES[0])
    apps_viejo = _apps_at_cuentas(CUENTAS_ANTES[0])
    UsuarioViejo = apps_viejo.get_model("cuentas", "Usuario")
    RolViejo = apps_viejo.get_model("cuentas", "Rol")

    rol_cliente_v = RolViejo.objects.get(nombre="cliente")
    assert UsuarioViejo.objects.get(pk=u.pk).rol_id == rol_cliente_v.pk

    # Limpia el rol extra creado en el esquema final para permitir reaplicar 0003.
    RolViejo.objects.filter(nombre="Moderador").delete()
    _migrate()