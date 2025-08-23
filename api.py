"""FastAPI application for TTS service orchestration."""
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from models import TTSConvertRequest, TTSConvertResponse, TTSTaskResponse, ErrorResponse
from database import DatabaseManager, get_database, Task
from tts_task_manager import TTSTaskManager
from tts_fb_service import FBTTSService


# Global service instances
tts_service: Optional[FBTTSService] = None
task_manager: Optional[TTSTaskManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global tts_service, task_manager
    
    # Startup
    try:
        # Initialize TTS service
        tts_service = FBTTSService()
        tts_service.start_service()
        
        # Initialize task manager
        task_manager = TTSTaskManager(tts_service=tts_service)
        task_manager.start_monitoring()
        
        print("API services initialized successfully")
    except Exception as e:
        print(f"Failed to initialize services: {e}")
        raise
    
    yield
    
    # Shutdown
    if task_manager:
        task_manager.stop_monitoring()
    
    if tts_service:
        tts_service.stop_service()
    
    print("API services shut down")


# Initialize FastAPI app
app = FastAPI(
    title="TTS API",
    description="Text-to-Speech conversion API that orchestrates with existing TTS services",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


def get_task_manager() -> TTSTaskManager:
    """Dependency to get the task manager instance."""
    global task_manager
    if task_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS service not initialized"
        )
    return task_manager


def get_tts_service() -> FBTTSService:
    """Dependency to get the TTS service instance."""
    global tts_service
    if tts_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TTS service not initialized"
        )
    return tts_service


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc)
        ).model_dump()
    )


@app.get("/", summary="Health check")
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "service": "TTS API", "version": "1.0.0"}


@app.post(
    "/api/v1/tts/convert",
    response_model=TTSConvertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit text for TTS conversion",
    description="Submit text for text-to-speech conversion. Returns conversion ID and status."
)
async def convert_text(
    request: TTSConvertRequest,
    task_mgr: TTSTaskManager = Depends(get_task_manager),
    db: DatabaseManager = Depends(get_database)
):
    """Submit text for TTS conversion."""
    try:
        # Submit task to TTS manager
        task_id = task_mgr.submit_task(
            text=request.text,
            custom_filename=request.custom_filename
        )
        
        if not task_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to submit TTS task"
            )
        
        # Get the created task from database
        task = db.get_task_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Task created but not found in database"
            )
        
        return TTSConvertResponse(
            conversion_id=task.task_id,
            text=task.original_text,
            status=task.status,
            submitted_at=task.submitted_at or task.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process TTS request: {str(e)}"
        )


@app.get(
    "/api/v1/tts/{conversion_id}",
    response_model=TTSTaskResponse,
    summary="Get TTS conversion status",
    description="Get the status and details of a TTS conversion task by ID."
)
async def get_conversion_status(
    conversion_id: str,
    db: DatabaseManager = Depends(get_database)
):
    """Get TTS conversion status and details."""
    try:
        # Get task from database
        task = db.get_task_by_id(conversion_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversion task with ID '{conversion_id}' not found"
            )
        
        # Calculate duration if file exists and has metadata
        duration = None
        if task.status == "completed" and task.output_file_path and os.path.exists(task.output_file_path):
            # Try to get duration from metadata first
            duration = task.duration
            
            # If not in metadata, calculate from file size and sampling rate
            if duration is None and task.file_size and task.sampling_rate:
                # Rough estimate: file_size / (sampling_rate * 2 bytes per sample)
                # This is approximate since it doesn't account for WAV header
                duration = task.file_size / (task.sampling_rate * 2)
        
        return TTSTaskResponse(
            conversion_id=task.task_id,
            text=task.original_text,
            status=task.status,
            output_file_path=task.output_file_path,
            custom_filename=task.custom_filename,
            submitted_at=task.submitted_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            failed_at=task.failed_at,
            file_size=task.file_size,
            sampling_rate=task.sampling_rate,
            duration=duration,
            device=task.device,
            error_message=task.error_message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve task status: {str(e)}"
        )


@app.get(
    "/api/v1/tts",
    response_model=list[TTSTaskResponse],
    summary="List TTS conversions",
    description="List TTS conversion tasks, optionally filtered by status."
)
async def list_conversions(
    status: Optional[str] = None,
    limit: int = 50,
    db: DatabaseManager = Depends(get_database)
):
    """List TTS conversion tasks."""
    try:
        # Validate status parameter
        if status and status not in ["queued", "processing", "completed", "failed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status. Must be one of: queued, processing, completed, failed"
            )
        
        # Validate limit
        if limit < 1 or limit > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 1000"
            )
        
        tasks = db.get_all_tasks(status=status, limit=limit)
        
        results = []
        for task in tasks:
            # Calculate duration if available
            duration = None
            if task.status == "completed" and task.output_file_path and os.path.exists(task.output_file_path):
                duration = task.duration
                if duration is None and task.file_size and task.sampling_rate:
                    duration = task.file_size / (task.sampling_rate * 2)
            
            results.append(TTSTaskResponse(
                conversion_id=task.task_id,
                text=task.original_text,
                status=task.status,
                output_file_path=task.output_file_path,
                custom_filename=task.custom_filename,
                submitted_at=task.submitted_at,
                started_at=task.started_at,
                completed_at=task.completed_at,
                failed_at=task.failed_at,
                file_size=task.file_size,
                sampling_rate=task.sampling_rate,
                duration=duration,
                device=task.device,
                error_message=task.error_message
            ))
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
