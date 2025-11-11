#!/usr/bin/with-contenv bashio
set -e

# Read options from add-on config
TZ=$(bashio::config 'timezone' 'UTC')
DEBUG=$(bashio::config 'debug' 'false')

# Export environment variables
export TZ="${TZ}"
export DEBUG="${DEBUG}"
export FLASK_ENV="production"
export FLASK_APP="app.py"
export DATA_DIR="/data"
export INGRESS="true"

# Log startup information
bashio::log.info "Starting ChoreControl..."
bashio::log.info "Timezone: ${TZ}"
bashio::log.info "Debug mode: ${DEBUG}"
bashio::log.info "Data directory: ${DATA_DIR}"

# Ensure data directory exists
mkdir -p "${DATA_DIR}"

# Initialize database if it doesn't exist
if [ ! -f "${DATA_DIR}/chorecontrol.db" ]; then
    bashio::log.info "Database not found. Initializing..."

    # Check if migrations directory exists
    if [ ! -d "migrations" ]; then
        bashio::log.info "Initializing Flask-Migrate..."
        flask db init || true
    fi

    # Create initial migration if needed
    if [ -z "$(ls -A migrations/versions 2>/dev/null)" ]; then
        bashio::log.info "Creating initial migration..."
        flask db migrate -m "Initial migration" || true
    fi
fi

# Run migrations to upgrade database schema
bashio::log.info "Running database migrations..."
flask db upgrade || {
    bashio::log.warning "Migration failed or no migrations to apply. Continuing..."
}

# Check database connectivity
if [ -f "${DATA_DIR}/chorecontrol.db" ]; then
    bashio::log.info "Database initialized successfully"
else
    bashio::log.warning "Database file not created. Will be created on first request."
fi

# Start Flask application
bashio::log.info "Starting Flask application on port 8099..."

# Use gunicorn for production (more robust than Flask dev server)
if command -v gunicorn &> /dev/null; then
    bashio::log.info "Using Gunicorn for production deployment"
    exec gunicorn \
        --bind 0.0.0.0:8099 \
        --workers 2 \
        --timeout 120 \
        --access-logfile - \
        --error-logfile - \
        app:app
else
    # Fallback to Flask dev server if gunicorn not available
    bashio::log.warning "Gunicorn not found, using Flask development server"
    exec flask run --host=0.0.0.0 --port=8099
fi
