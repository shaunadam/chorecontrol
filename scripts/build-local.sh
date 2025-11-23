#!/bin/bash
set -e

# Build and test ChoreControl Docker image locally
# Usage: ./scripts/build-local.sh [--run]

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ADDON_DIR="$PROJECT_DIR/chorecontrol"

# Extract version from config.yaml
VERSION=$(grep '^version:' "$ADDON_DIR/config.yaml" | sed 's/version: *"\(.*\)"/\1/')
IMAGE_NAME="chorecontrol-local:$VERSION"

echo "Building ChoreControl $VERSION..."
echo "================================"

# Build the image
docker build \
    --build-arg BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.11-alpine3.18 \
    -t "$IMAGE_NAME" \
    -t "chorecontrol-local:latest" \
    "$ADDON_DIR"

echo ""
echo "Build successful: $IMAGE_NAME"
echo ""

# Run if requested
if [ "$1" == "--run" ]; then
    echo "Starting container..."
    echo "===================="

    # Create data directory if it doesn't exist
    mkdir -p "$PROJECT_DIR/data"

    # Stop existing container if running
    docker rm -f chorecontrol-test 2>/dev/null || true

    # Run the container
    docker run -d \
        --name chorecontrol-test \
        -p 8099:8099 \
        -v "$PROJECT_DIR/data:/data" \
        -e TZ=UTC \
        "$IMAGE_NAME"

    echo ""
    echo "Container started!"
    echo "  - Web UI: http://localhost:8099"
    echo "  - Logs:   docker logs -f chorecontrol-test"
    echo "  - Stop:   docker stop chorecontrol-test"
    echo ""
else
    echo "To run the container:"
    echo "  ./scripts/build-local.sh --run"
    echo ""
    echo "Or manually:"
    echo "  docker run -p 8099:8099 -v \$(pwd)/data:/data $IMAGE_NAME"
fi
