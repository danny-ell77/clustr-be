#!/bin/bash
set -e

# Ensure Python can find the app modules
export PYTHONPATH="${PYTHONPATH}:/app"

# Ensure database exists
echo "Ensuring database exists..."
python scripts/ensure_db_exists.py

# Run migrations
echo "Running migrations..."
python manage.py migrate --no-input

# Start the application
echo "Starting application..."
exec "$@"
