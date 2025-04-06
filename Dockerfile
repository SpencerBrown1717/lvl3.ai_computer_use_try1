FROM python:3.10-slim

# Install X11, VNC, and other dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    xterm \
    fluxbox \
    wget \
    curl \
    firefox-esr \
    libx11-dev \
    libxtst-dev \
    libpng-dev \
    libjpeg-dev \
    libopencv-dev \
    python3-tk \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install python-dotenv
RUN pip install --no-cache-dir python-dotenv

# Copy the rest of the application
COPY . .

# Set up a virtual display
ENV DISPLAY=:1

# Create a startup script
RUN echo '#!/bin/bash\n\
# Start virtual display\n\
Xvfb $DISPLAY -screen 0 1280x800x24 &\n\
sleep 1\n\
x11vnc -display $DISPLAY -forever -nopw &\n\
fluxbox &\n\
\n\
# Start MCP server\n\
echo "Starting MCP server..."\n\
python /app/mcp_server.py &\n\
MCP_PID=$!\n\
\n\
# Wait for MCP server to be ready\n\
echo "Waiting for MCP server to be ready..."\n\
for i in {1..10}; do\n\
  if curl -s http://localhost:5000/api/v1/status > /dev/null; then\n\
    echo "MCP server is ready!"\n\
    break\n\
  fi\n\
  echo "Waiting for MCP server... $i/10"\n\
  sleep 2\n\
done\n\
\n\
# Start main application\n\
echo "Starting main application..."\n\
python /app/main.py\n\
\n\
# Keep container running if main app exits\n\
wait $MCP_PID\n\
' > /app/start.sh \
    && chmod +x /app/start.sh

# Expose VNC port and MCP server port
EXPOSE 5900 5000

# Command to run
CMD ["/app/start.sh"]
