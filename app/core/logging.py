"""Logging configuration for the application."""

import logging
import sys
from pathlib import Path
from typing import Optional

from app.core.config import settings


def setup_logging(log_level: str = None, log_file: Optional[str] = None) -> logging.Logger:
    """Configure logging for the application."""
    if log_level is None:
        log_level = settings.log_level
    
    # Create a custom formatter for consistent alignment
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S,%f'[:-3]  # Format: YYYY-MM-DD HH:MM:SS,mmm
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create and configure handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)
    
    # Intercept Uvicorn logs and format them consistently
    uvicorn_logger = logging.getLogger("uvicorn")
    for handler in uvicorn_logger.handlers[:]:
        uvicorn_logger.removeHandler(handler)
    
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    for handler in uvicorn_access_logger.handlers[:]:
        uvicorn_access_logger.removeHandler(handler)
    
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    for handler in uvicorn_error_logger.handlers[:]:
        uvicorn_error_logger.removeHandler(handler)
    
    return logging.getLogger(__name__)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module."""
    return logging.getLogger(name)
