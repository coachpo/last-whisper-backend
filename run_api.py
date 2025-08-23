#!/usr/bin/env python3
"""Script to run the TTS API server."""
import uvicorn

from app.core.config import settings


def main():
    """Run the API server."""
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
