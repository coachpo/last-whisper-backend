# Multi-stage build for Last Whisper Backend
FROM python:3.12-slim AS base

# Set default environment variables
ENV ENVIRONMENT=production \
    TTS_PROVIDER=gcp \
    LOG_LEVEL=info \
    CORS_ORIGINS=http://localhost:8008

# Create non-root user with home directory
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY run_api.py .

# Create necessary directories and set permissions
RUN mkdir -p audio keys data && \
    chown -R appuser:appuser /app && \
    chown -R appuser:appuser /home/appuser

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Default command - use Gunicorn with Uvicorn workers for production
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-"]
