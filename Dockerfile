# Multi-stage Dockerfile for Provenance Logger on Jetson Orin Nano
# Base: NVIDIA JetPack L4T runtime (JetPack 6.0)
# Architecture: aarch64

# ==============================================================================
# Stage 1: Python Core (logger + verifier)
# ==============================================================================
FROM nvcr.io/nvidia/l4t-jetpack:r36.3.0 AS python-core

LABEL maintainer="Provenance Stack"
LABEL description="Provenance Logger for Jetson Orin Nano - Python Core"

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Python 3.10+
    python3.10 \
    python3-pip \
    python3-dev \
    # GStreamer
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    python3-gst-1.0 \
    # OpenCV dependencies
    libopencv-dev \
    python3-opencv \
    # Hardware interfaces
    can-utils \
    i2c-tools \
    # Utilities
    v4l-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python3 -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Install Python packages
RUN pip3 install --no-cache-dir \
    # Core dependencies
    python-can==4.3.1 \
    pyserial==3.5 \
    cryptography==42.0.5 \
    PyNaCl==1.5.0 \
    PyYAML==6.0.1 \
    SQLAlchemy==2.0.29 \
    Flask==3.0.3 \
    Flask-Cors==4.0.0 \
    # Additional utilities
    Pillow==10.3.0 \
    numpy==1.26.4 \
    requests==2.31.0

# Create application directories
RUN mkdir -p /app/python_core /data /config /keys

# Set working directory
WORKDIR /app

# Copy Python core files
COPY python_core/ /app/python_core/
COPY config/config.example.yaml /config/
COPY entrypoint.sh /app/

# Make entrypoint executable
RUN chmod +x /app/entrypoint.sh

# Create mount points
VOLUME ["/data", "/config", "/keys"]

# Expose Flask API port
EXPOSE 5000

# Default entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["logger"]

# ==============================================================================
# Stage 2: Node.js UI (optional)
# ==============================================================================
FROM python-core AS node-ui

LABEL description="Provenance Logger with optional Node.js dashboard"

# Install Node.js 18.x
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy Node.js UI files
COPY node_ui/ /app/node_ui/

# Install Node.js dependencies
WORKDIR /app/node_ui
RUN npm install --omit=dev --no-audit --no-fund

# Expose Node.js dashboard port
EXPOSE 8080

# Switch back to app directory
WORKDIR /app

# Entrypoint remains the same (handles both modes)
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["logger"]
