FROM python:3.10-slim

# Install X11, VNC, and other dependencies
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    xterm \
    fluxbox \
    wget \
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

# Copy the rest of the application
COPY . .

# Set up a virtual display
ENV DISPLAY=:1

# Create a startup script
RUN echo '#!/bin/bash\nXvfb $DISPLAY -screen 0 1280x800x24 &\nsleep 1\nx11vnc -display $DISPLAY -forever -nopw &\nfluxbox &\npython /app/main.py' > /app/start.sh \
    && chmod +x /app/start.sh

# Expose VNC port
EXPOSE 5900

# Command to run
CMD ["/app/start.sh"]
