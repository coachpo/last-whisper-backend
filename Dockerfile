# Multi-stage build for Last Whisper Backend
FROM python:3.12-alpine AS base

# Set default environment variables
ENV ENVIRONMENT=production \
    TTS_PROVIDER=gcp \
    LOG_LEVEL=info \
    HOST=0.0.0.0 \
    PORT=8000 \
    APP_NAME="Last Whisper Backend" \
    APP_VERSION="1.0.0" \
    DATABASE_URL=sqlite:///data/dictation.db \
    AUDIO_DIR=audio \
    TTS_SUPPORTED_LANGUAGES=fi \
    CORS_ORIGINS=http://localhost:3000,http://127.0.1:3000 \
    CORS_ALLOW_METHODS="*" \
    CORS_ALLOW_HEADERS="*" \
    DOCS_URL="/docs" \
    REDOC_URL="/redoc" \
    OPENAPI_URL="/openapi.json"

# Create non-root user with home directory
RUN addgroup -S appuser && adduser -S -G appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create necessary directories and set permissions
RUN mkdir -p audio keys data && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Default command - use Gunicorn with Uvicorn workers for production
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
