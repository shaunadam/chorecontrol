#!/usr/bin/with-contenv bashio
set -e

# Read configuration from Home Assistant addon options
if bashio::config.exists 'timezone'; then
    TZ="$(bashio::config 'timezone')"
else
    TZ="America/Denver"
fi

if bashio::config.exists 'debug'; then
    DEBUG="$(bashio::config 'debug')"
else
    DEBUG="false"
fi

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

# Clear Python bytecode cache to ensure latest code is loaded
# This prevents issues with cached .pyc files from previous versions
echo "Clearing Python bytecode cache..."
find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find /app -type f -name "*.pyc" -delete 2>/dev/null || true

# Run database migrations
echo "Running database migrations..."
echo "Database URI: sqlite:///${DATA_DIR}/chorecontrol.db"

# Show migration status first
echo "Checking migration status..."
flask db current || echo "No current migration found"

# Run the upgrade
if flask db upgrade; then
    echo "Database migrations completed successfully"
    flask db current
else
    echo "Error: Database migration failed!"
    echo "Attempting to show migration history..."
    flask db history || true
    exit 1
fi

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
        --log-level info \
        --access-logfile - \
        --error-logfile - \
        app:app
else
    # Fallback to Flask dev server if gunicorn not available
    echo "Warning: Gunicorn not found, using Flask development server"
    exec flask run --host=0.0.0.0 --port=8099
fi
