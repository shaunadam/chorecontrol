ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18
FROM $BUILD_FROM

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    sqlite \
    sqlite-dev

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY config.py .
COPY models.py .
COPY schemas.py .
COPY seed.py .
COPY seed_helpers.py .
COPY __init__.py .
COPY run.sh .

# Make run script executable
RUN chmod +x run.sh

# Create data directory for SQLite database
RUN mkdir -p /data

# Expose port (HA add-ons typically use ingress, but expose for flexibility)
EXPOSE 8099

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV DATA_DIR=/data

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8099/health || exit 1

# Run the application via startup script
CMD ["/app/run.sh"]
