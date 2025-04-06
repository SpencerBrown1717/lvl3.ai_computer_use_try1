#!/bin/bash
# Start script for Computer Control Agent Docker container

# Set up display
echo "Setting up virtual display..."
Xvfb :1 -screen 0 1280x800x24 &
sleep 2

# Start VNC server
echo "Starting VNC server..."
x11vnc -display :1 -nopw -listen 0.0.0.0 -xkb -forever &
sleep 2

# Create necessary directories
mkdir -p /app/screenshots
mkdir -p /app/reference_images

# Start MCP server
echo "Starting MCP server..."
python -m src.api.mcp_server &
MCP_PID=$!

# Wait for MCP server to be ready
echo "Waiting for MCP server to be ready..."
until $(curl --output /dev/null --silent --fail http://localhost:${MCP_PORT:-5000}/api/v1/status); do
    printf '.'
    sleep 1
done
echo "MCP server is ready!"

# Start main application
echo "Starting main application..."
python -m main

# Keep container running if main app exits
wait $MCP_PID
