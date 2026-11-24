# Procedimiento de migraciones (ACT-002)

## Integrar una cadena de ramas

1. Calcula el **merge-base real** contra `origin/main` (puede haber force push).
2. Previsualiza sin tocar el árbol: `git merge-tree --write-tree HEAD origin/main`.
3. Integra con un solo PR: `git merge --no-commit --no-ff origin/main`. Nunca rebasees ni reescribas historia.
4. Migraciones: si una app queda con varios nodos hoja, usa `makemigrations --merge` o ajusta las dependencias **solo de las migraciones nuevas de la cadena**. No edites ni renumere migraciones que ya están en `main`; si los nombres colisionan, pregunta antes.
5. Conflictos: conserva `main` en frontend, Docker, docs de sprint y CI; conserva la cadena en modelos, migraciones, pruebas de normalización y docs de datos. El código de `backend/api/` se trata en su propio issue.

## Orden de verificación

1. `makemigrations --check --dry-run` y `manage.py check` con los settings de prueba.
2. **BD vacía**: `migrate --noinput` y `migrate --check`; deben aplicarse todas las migraciones.
3. **Con datos**: migra primero solo `main`, siembra con `seed_catalogo`, crea usuarios/pedidos/pagos de prueba y migra al estado final; comprueba que las filas originales siguen ahí y que los catálogos nuevos se crearon.
4. **Reversión**: desaplica hasta las hojas de `main` y vuelve a leer los datos con el código de `main`.
5. Suite completa de pytest con la configuración del CI. Nunca saltes ni borres pruebas para ponerla en verde.

 Usa siempre bases temporales y `DATABASE_URL` explícito: **nunca migres contra `backend/.env`**.

## Reglas aprendidas

- **Separa esquema y datos**: una migración crea/altera tablas; otra backfillea y siembra catálogos. Los backfills deben ser idempotentes y por lotes.
- **Orden de reversión**: hijos antes que padres. En esta cadena: `inventario` → `pagos` → `pedidos` → `cuentas` → `catalogo`, dejando cada app en la migración que tenía `main`.
- **No edites migraciones aplicadas**: cualquier corrección va en una migración nueva.
- **Catálogos y flush**: las pruebas transaccionales hacen `flush` y vacían los catálogos; una fixture `autouse` los vuelve a sembrar y tolera `DatabaseError` mientras el esquema es intermedio.
- **SQLite vs PostgreSQL**: SQLite necesita `transaction_mode=IMMEDIATE` para los tests con hilos; PostgreSQL valida FKs y constraints de forma distinta. Prueba ambos motores antes de cerrar la integración.

## Procedimiento de rollback

```bash
python manage.py migrate inventario zero --noinput
python manage.py migrate pagos 0001 --noinput
python manage.py migrate pedidos 0002 --noinput
python manage.py migrate cuentas 0001 --noinput
python manage.py migrate catalogo 0002 --noinput
python manage.py showmigrations      # solo las hojas de main deben estar aplicadas
python manage.py migrate --check     # limpio desde el código de main
```

Si las tablas que se eliminan contienen datos nuevos, exporta esas filas antes de desaplicar. El rollback de BD es independiente de git: no implica borrar commits ni tocar otras ramas.
