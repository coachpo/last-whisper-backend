# Docker Setup Documentation - Last Whisper Backend

## Overview

This document describes the Docker configuration and deployment setup for the Last Whisper backend service, a FastAPI application providing Text-to-Speech (TTS) capabilities with multiple providers (Local, Azure, Google Cloud) and dictation training features.

## Files Created/Modified

### 1. Dockerfile
- **Purpose**: Production-ready container configuration
- **Base Image**: Python 3.11-slim
- **Features**: Multi-stage build, security hardening, production WSGI server

### 2. .dockerignore
- **Purpose**: Optimize Docker build by excluding unnecessary files
- **Excludes**: Python artifacts, development files, runtime data, credentials

### 3. app/core/config.py
- **Purpose**: Enhanced configuration with production settings
- **Added**: Environment detection, documentation control, credential management

### 4. app/main.py
- **Purpose**: Conditional documentation endpoint configuration
- **Feature**: Disables docs in production for security

## Docker Configuration

### Base Configuration
```dockerfile
FROM python:3.11-slim AS base

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENVIRONMENT=production \
    DISABLE_DOCS=true \
    RELOAD=false \
    LOG_LEVEL=info
```

**Note**: `GOOGLE_APPLICATION_CREDENTIALS` is intentionally not set in the Dockerfile for security reasons. It should be provided at runtime.

### Security Features
- **Non-root user**: Runs as `appuser` instead of root
- **Minimal base image**: Uses Python slim image for smaller attack surface
- **Credential protection**: Keys directory excluded from image build

### Production Server
- **WSGI Server**: Gunicorn with Uvicorn workers
- **Configuration**: 4 workers, ASGI support for FastAPI
- **Logging**: Structured logging to stdout/stderr for Docker

## Environment Configuration

### Development vs Production

| Setting | Development | Production (Docker) |
|---------|-------------|-------------------|
| `environment` | "development" | "production" |
| `disable_docs` | false | true |
| `reload` | true | false |
| `log_level` | "info" | "info" |
| `google_application_credentials` | "keys/google-credentials.json" | "/app/keys/google-credentials.json" |

### Documentation Endpoints
- **Development**: `/docs`, `/redoc`, `/openapi.json` enabled
- **Production**: All documentation endpoints disabled (return 404)

## Build and Deployment

### Building the Image
```bash
docker build -t last-whisper-backend .
```

### Running the Container

#### Basic Run
```bash
docker run -p 8000:8000 last-whisper-backend
```

#### With Google Cloud Credentials
```bash
docker run -e GOOGLE_APPLICATION_CREDENTIALS=/app/keys/google-credentials.json \
  -v /path/to/credentials.json:/app/keys/google-credentials.json \
  -p 8000:8000 last-whisper-backend
```

#### With Custom Configuration
```bash
docker run -e TTS_PROVIDER=azure \
  -e AZURE_SPEECH_KEY=your_key \
  -e AZURE_SPEECH_REGION=your_region \
  -p 8000:8000 last-whisper-backend
```

## TTS Provider Configuration

### Local TTS (Default)
- **Model**: Facebook MMS-TTS-Fin
- **Requirements**: PyTorch, Transformers
- **Device**: Auto-detection (GPU/CPU)

### Azure Speech TTS
```bash
docker run -e TTS_PROVIDER=azure \
  -e AZURE_SPEECH_KEY=your_azure_key \
  -e AZURE_SPEECH_REGION=your_azure_region \
  -p 8000:8000 last-whisper-backend
```

### Google Cloud TTS
```bash
docker run -e TTS_PROVIDER=gcp \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/keys/google-credentials.json \
  -v /path/to/credentials.json:/app/keys/google-credentials.json \
  -p 8000:8000 last-whisper-backend
```

## Health Monitoring

### Health Check
```dockerfile
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
```

### Endpoints
- **Health Check**: `GET /health`
- **API Documentation**: `GET /docs` (disabled in production)
- **OpenAPI Spec**: `GET /openapi.json` (disabled in production)

## File Structure in Container

```
/app/
├── app/                    # Application code
│   ├── api/               # API routes and dependencies
│   ├── core/              # Configuration and utilities
│   ├── models/            # Database models and schemas
│   ├── services/          # Business logic services
│   └── tts_engine/        # TTS engine implementations
├── audio/                 # Generated audio files (created at runtime)
├── keys/                  # Credential files (mounted at runtime)
├── run_api.py            # Application entry point
└── requirements.txt      # Python dependencies
```

## Security Considerations

### Credentials Management
- **Development**: Uses local `keys/google-credentials.json`
- **Production**: Credentials mounted as volumes or passed as environment variables
- **Docker**: Credentials excluded from image build (`.dockerignore`)

### Network Security
- **Port**: Exposes only port 8000
- **CORS**: Configured for frontend integration
- **Documentation**: Disabled in production

### Runtime Security
- **User**: Runs as non-root user (`appuser`)
- **Permissions**: Proper file ownership and permissions
- **Logging**: Structured logging without sensitive data exposure

## Performance Optimization

### Docker Build
- **Layer Caching**: Requirements copied first for better caching
- **Multi-stage**: Optimized for production deployment
- **Size**: Minimal dependencies and excluded unnecessary files

### Runtime Performance
- **Workers**: 4 Gunicorn workers for concurrent request handling
- **ASGI**: Full async support for FastAPI
- **GPU Support**: Automatic device detection for local TTS

## Troubleshooting

### Common Issues

#### Credentials Not Found
```bash
# Ensure credentials file is mounted correctly and environment variable is set
docker run -e GOOGLE_APPLICATION_CREDENTIALS=/app/keys/google-credentials.json \
  -v $(pwd)/keys/google-credentials.json:/app/keys/google-credentials.json \
  -p 8000:8000 last-whisper-backend
```

#### TTS Provider Issues
```bash
# Check provider configuration
docker run -e TTS_PROVIDER=local -p 8000:8000 last-whisper-backend
```

#### Health Check Failures
```bash
# Check container logs
docker logs <container_id>
```

### Logs and Debugging
```bash
# View container logs
docker logs -f <container_id>

# Access container shell
docker exec -it <container_id> /bin/bash

# Check environment variables
docker exec <container_id> env
```

## Production Deployment

### Docker Compose (Recommended)
```yaml
version: '3.8'
services:
  last-whisper-backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./keys:/app/keys:ro
      - ./audio:/app/audio
    environment:
      - TTS_PROVIDER=gcp
      - ENVIRONMENT=production
    restart: unless-stopped
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: last-whisper-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: last-whisper-backend
  template:
    metadata:
      labels:
        app: last-whisper-backend
    spec:
      containers:
      - name: backend
        image: last-whisper-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: TTS_PROVIDER
          value: "gcp"
        - name: ENVIRONMENT
          value: "production"
        volumeMounts:
        - name: credentials
          mountPath: /app/keys
          readOnly: true
      volumes:
      - name: credentials
        secret:
          secretName: google-credentials
```

## Monitoring and Maintenance

### Health Monitoring
- **Health Check**: Built-in Docker health check
- **Logs**: Structured JSON logging
- **Metrics**: Application metrics via `/health` endpoint

### Updates and Maintenance
```bash
# Rebuild image with updates
docker build -t last-whisper-backend:latest .

# Update running container
docker-compose up -d --build
```

## Recent Updates and Fixes

### Docker Build Improvements (Latest)
- **Fixed FROM/AS casing**: Changed to `FROM python:3.11-slim AS base` for Docker best practices
- **Removed sensitive data from ENV**: `GOOGLE_APPLICATION_CREDENTIALS` no longer in Dockerfile for security
- **Simplified package installation**: Removed unnecessary `software-properties-common` package
- **Better cleanup**: Added `apt-get clean` for smaller image size
- **Security compliance**: No more Docker security warnings during build

### Security Enhancements
- **Runtime credentials**: Google Cloud credentials must be provided at runtime via `-e` flag
- **No hardcoded secrets**: All sensitive data excluded from Docker image
- **Clean builds**: Optimized package installation and cleanup

### Build Process
```bash
# Build without warnings
docker build -t last-whisper-backend .

# Run with proper credential handling
docker run -e GOOGLE_APPLICATION_CREDENTIALS=/app/keys/google-credentials.json \
  -v /path/to/credentials.json:/app/keys/google-credentials.json \
  -p 8000:8000 last-whisper-backend
```

## Conclusion

This Docker setup provides a production-ready, secure, and scalable deployment solution for the Last Whisper backend service. The configuration supports multiple TTS providers, proper credential management, and follows Docker best practices for security and performance.

**Key Features:**
- ✅ Security-hardened (no secrets in image)
- ✅ Production-ready WSGI server
- ✅ Multi-provider TTS support
- ✅ Environment-based configuration
- ✅ Clean Docker builds without warnings

For additional support or questions, refer to the main project documentation or create an issue in the repository.
