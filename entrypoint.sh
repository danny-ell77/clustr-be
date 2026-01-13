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

# Load initial data if database is empty
echo "Checking initial data..."
python scripts/load_initial_data.py

# Start the application
echo "Starting application..."
exec "$@"
