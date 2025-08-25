"""Audio serving endpoints."""

import os

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import settings

router = APIRouter()


@router.get("/v1/audio/{filename}")
async def serve_audio(filename: str):
    """Serve audio files."""
    # Validate filename for security
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    if not filename.endswith('.wav'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only WAV files are supported",
        )

    audio_path = os.path.join(settings.audio_dir, filename)

    if not os.path.exists(audio_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audio file not found",
        )

    return FileResponse(
        path=audio_path,
        media_type="audio/wav",
        filename=filename,
    )
