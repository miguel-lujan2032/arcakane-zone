#!/usr/bin/env sh
set -eu

is_true() {
  case "${1:-}" in
    true|TRUE|True|1|yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

: "${SECRET_KEY:?SECRET_KEY is required}"

echo "Waiting for the database..."
python - <<'PY'
import os
import sys
import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "arkane_zone.settings")

import django

django.setup()

from django.db import connections
from django.db.utils import OperationalError

for attempt in range(1, 31):
    try:
        connections["default"].ensure_connection()
        print("Database is ready.")
        break
    except OperationalError as exc:
        print(f"Database not ready ({attempt}/30): {exc}", file=sys.stderr)
        time.sleep(2)
else:
    sys.exit("Database did not become ready in time.")
PY

echo "Preparing cache table..."
python manage.py createcachetable

if is_true "${RUN_MIGRATIONS:-true}"; then
  echo "Applying database migrations..."
  python manage.py migrate --noinput
fi

if is_true "${COLLECTSTATIC:-true}"; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

if is_true "${SEED_CATALOGO:-false}"; then
  echo "Seeding catalog..."
  python manage.py seed_catalogo
fi

exec "$@"
