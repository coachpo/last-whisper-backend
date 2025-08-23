"""Pydantic models for API request/response schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TTSConvertRequest(BaseModel):
    """Request model for TTS conversion."""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to convert to speech")
    custom_filename: Optional[str] = Field(None, max_length=255,
                                           description="Optional custom filename (without extension)")


class TTSConvertResponse(BaseModel):
    """Response model for TTS conversion submission."""
    conversion_id: str = Field(..., description="Unique ID for the conversion task")
    text: str = Field(..., description="Echo of the submitted text")
    status: str = Field(..., description="Current status of the conversion")
    submitted_at: datetime = Field(..., description="Timestamp when the task was submitted")


class TTSTaskResponse(BaseModel):
    """Response model for TTS task status and details."""
    conversion_id: str = Field(..., description="Unique ID for the conversion task")
    text: str = Field(..., description="Original text submitted for conversion")
    status: str = Field(..., description="Current status: queued, processing, completed, failed")
    output_file_path: Optional[str] = Field(None, description="Path to the generated audio file (when completed)")
    custom_filename: Optional[str] = Field(None, description="Custom filename specified in request")

    # Timestamps
    submitted_at: Optional[datetime] = Field(None, description="When the task was submitted")
    started_at: Optional[datetime] = Field(None, description="When processing started")
    completed_at: Optional[datetime] = Field(None, description="When processing completed")
    failed_at: Optional[datetime] = Field(None, description="When the task failed")

    # Audio metadata (when completed)
    file_size: Optional[int] = Field(None, description="File size in bytes")
    sampling_rate: Optional[int] = Field(None, description="Audio sampling rate in Hz")
    duration: Optional[float] = Field(None, description="Audio duration in seconds")

    # Processing metadata
    device: Optional[str] = Field(None, description="Device used for processing")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class ErrorResponse(BaseModel):
    """Response model for API errors."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: datetime = Field(..., description="Current timestamp")
