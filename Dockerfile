# Multi-stage build for Last Whisper Backend
FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENVIRONMENT=production \
    DISABLE_DOCS=true \
    RELOAD=false \
    TTS_PROVIDER=local \
    LOG_LEVEL=info \
    HF_HOME=/app/.cache/huggingface \
    CORS_ORIGINS=http://192.168.31.177:8008

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user with home directory
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Gunicorn for production WSGI server
RUN pip install --no-cache-dir gunicorn

# Copy application code
COPY app/ ./app/
COPY run_api.py .

# Create necessary directories and set permissions
RUN mkdir -p audio keys && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /home/appuser

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command - use Gunicorn with Uvicorn workers for production
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
