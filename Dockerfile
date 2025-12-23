# Multi-stage build for The Gold Trader's Edge
# This Docker image runs both the API and Signal Generation service

FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY packages/api/requirements.txt /app/api-requirements.txt
COPY packages/engine/requirements.txt /app/engine-requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/api-requirements.txt
RUN pip install --no-cache-dir -r /app/engine-requirements.txt
RUN pip install --no-cache-dir uvicorn[standard]

# Copy application code
COPY packages/api /app/api
COPY packages/engine /app/engine

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Set Python path
ENV PYTHONPATH=/app/engine/src:/app/api/src:$PYTHONPATH

# Set default port (Railway will override)
ENV PORT=8000

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:${PORT:-8000}/health')"

# Run both API and Signal Generator via supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
