"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.api.routes import health, tts
from app.core.config import settings
from app.core.exceptions import TTSAPIException
from app.models.schemas import ErrorResponse
from app.services.tts_service import tts_service
from app.services.task_manager import task_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    # Startup
    try:
        # Initialize TTS service
        tts_service.initialize()
        print("TTS service initialized successfully")
        
        # Initialize task manager
        task_manager.initialize()
        print("Task manager initialized successfully")
        
        print("API services initialized successfully")
    except Exception as e:
        print(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        task_manager.shutdown()
        print("Task manager shut down")
        
        tts_service.shutdown()
        print("TTS service shut down")
        
        print("API services shut down")
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
    lifespan=lifespan
)


@app.exception_handler(TTSAPIException)
async def tts_api_exception_handler(request, exc: TTSAPIException):
    """Handle TTS API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.message,
            detail=exc.detail
        ).model_dump(),
        headers=exc.headers
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).model_dump()
    )


# Include routers
app.include_router(health.router)
app.include_router(tts.router)
