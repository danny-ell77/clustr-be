#!/bin/bash
set -e

# Ensure database exists
echo "Ensuring database exists..."
python scripts/ensure_db_exists.py

# Run migrations
echo "Running migrations..."
python manage.py migrate --no-input

# Start the application
echo "Starting application..."
exec "$@"
