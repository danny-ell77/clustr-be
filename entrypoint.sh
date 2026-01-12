#!/bin/bash
set -e

# Ensure database exists
echo "Ensuring database exists..."
python scripts/ensure_db_exists.py

# Start the application
echo "Starting application..."
exec "$@"
