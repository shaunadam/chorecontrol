#!/bin/sh
set -e

# Set default environment variables
TZ="${TZ:-UTC}"
DEBUG="${DEBUG:-false}"

# Export environment variables
export TZ="${TZ}"
export DEBUG="${DEBUG}"
export FLASK_ENV="production"
export FLASK_APP="app.py"
export DATA_DIR="/data"
export INGRESS="true"

# Log startup information
echo "Starting ChoreControl..."
echo "Timezone: ${TZ}"
echo "Debug mode: ${DEBUG}"
echo "Data directory: ${DATA_DIR}"

# Ensure data directory exists
mkdir -p "${DATA_DIR}"

# Change to app directory and set Python path (ensure Python can find modules)
cd /app
export PYTHONPATH=/app

# Run database migrations
echo "Running database migrations..."
flask db upgrade || {
    echo "Error: Database migration failed!"
    exit 1
}

# Check database connectivity
if [ -f "${DATA_DIR}/chorecontrol.db" ]; then
    echo "Database initialized successfully"
else
    echo "Warning: Database file not created. Will be created on first request."
fi

# Start Flask application
echo "Starting Flask application on port 8099..."

# Use gunicorn for production (more robust than Flask dev server)
if command -v gunicorn > /dev/null 2>&1; then
    echo "Using Gunicorn for production deployment"
    exec gunicorn \
        --bind 0.0.0.0:8099 \
        --workers 2 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile - \
        app:app
else
    # Fallback to Flask dev server if gunicorn not available
    echo "Warning: Gunicorn not found, using Flask development server"
    exec flask run --host=0.0.0.0 --port=8099
fi
