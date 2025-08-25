"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.dependencies import get_enhanced_task_manager, get_database_manager
from app.api.routes import health, tts, items, attempts, stats
from app.core.config import settings
from app.core.exceptions import TTSAPIException
from app.models.schemas import ErrorResponse
from app.services.outer.tts_service import tts_service
from app.services.task_manager import task_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    try:
        # Initialize database manager
        db_manager = get_database_manager()
        print("Database manager initialized successfully")

        # Initialize TTS service
        tts_service.initialize()
        print("TTS service initialized successfully")

        # Initialize legacy task manager
        task_manager.initialize()
        print("Legacy task manager initialized successfully")

        # Initialize enhanced task manager
        enhanced_task_manager = get_enhanced_task_manager()
        enhanced_task_manager.start_monitoring()
        print("Enhanced task manager initialized successfully")

        print("All API services initialized successfully")
    except Exception as e:
        print(f"Failed to initialize services: {e}")
        raise

    yield

    # Shutdown
    try:
        # Shutdown enhanced task manager
        try:
            enhanced_task_manager = get_enhanced_task_manager()
            enhanced_task_manager.stop_monitoring()
            print("Enhanced task manager shut down")
        except Exception as e:
            print(f"Error shutting down enhanced task manager: {e}")

        # Shutdown legacy task manager
        task_manager.shutdown()
        print("Legacy task manager shut down")

        # Shutdown TTS service
        tts_service.shutdown()
        print("TTS service shut down")

        print("All API services shut down")
    except Exception as e:
        print(f"Error during shutdown: {e}")


# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    openapi_url=settings.openapi_url,
    lifespan=lifespan,
)


@app.exception_handler(TTSAPIException)
async def tts_api_exception_handler(request, exc: TTSAPIException):
    """Handle TTS API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.message, detail=exc.detail).model_dump(),
        headers=exc.headers,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Internal server error", detail=str(exc)).model_dump(),
    )


# Include routers
app.include_router(health.router)
app.include_router(tts.router)
app.include_router(items.router)
app.include_router(attempts.router)
app.include_router(stats.router)
