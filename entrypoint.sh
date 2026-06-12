#!/bin/bash
set -e

# Ensure Python can find the app modules
export PYTHONPATH="${PYTHONPATH}:/app"

# Ensure database exists
echo "Ensuring database exists..."
python scripts/ensure_db_exists.py

# Run migrations to apply any pending schema changes
echo "Running migrations..."
if ! python manage.py migrate --no-input; then
    echo "ERROR: migrate failed. Aborting startup." >&2
    exit 1
fi

# Check whether any tables were actually created. If the database is still
# empty after migrate (e.g. first-ever boot with no migration history),
# fall back to --run-syncdb so Django creates the schema directly from the
# current model state.
echo "Verifying schema..."
TABLE_COUNT=$(python manage.py shell -c "
from django.db import connection
with connection.cursor() as c:
    c.execute(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'\")
    print(c.fetchone()[0])
" 2>/dev/null || echo "0")

if [ "$TABLE_COUNT" -eq "0" ]; then
    echo "No tables found after migrate — running migrate --run-syncdb to force schema creation..."
    if ! python manage.py migrate --run-syncdb --no-input; then
        echo "ERROR: migrate --run-syncdb failed. Aborting startup." >&2
        exit 1
    fi
    echo "Schema creation complete."
else
    echo "Schema verified: ${TABLE_COUNT} table(s) present."
fi

# Start the application
echo "Starting application..."
exec "$@"
