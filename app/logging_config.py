"""
Logging Configuration
Phase 10: Integration & Polish
"""
import sys
import json
from loguru import logger
from datetime import datetime
from pathlib import Path


def setup_logging(debug: bool = False):
    """
    Configure application logging.
    
    Args:
        debug: If True, use human-readable format. If False, use JSON format.
        
    Returns:
        Configured logger instance
    """
    # Remove default handler
    logger.remove()
    
    # JSON format for production
    def json_format(record):
        """Format log record as JSON for production."""
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "module": record["name"],
            "function": record["function"],
            "line": record["line"]
        }
        
        # Add extra fields
        if record["extra"]:
            log_record["extra"] = record["extra"]
        
        # Add exception info
        if record["exception"]:
            log_record["exception"] = str(record["exception"])
        
        return json.dumps(log_record)
    
    # Console output
    if debug:
        # Human-readable format for development
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="DEBUG",
            colorize=True
        )
    else:
        # JSON format for production
        logger.add(
            sys.stdout,
            format="{message}",
            level="INFO",
            serialize=True  # This enables JSON output
        )
    
    # File output (optional - only if path exists)
    log_dir = Path("/var/log/armlenquant")
    if log_dir.exists():
        # Main log file with rotation
        logger.add(
            log_dir / "api.log",
            rotation="100 MB",
            retention="7 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
        
        # Error log file
        logger.add(
            log_dir / "error.log",
            rotation="50 MB",
            retention="30 days",
            level="ERROR",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
        )
    
    return logger


def get_logger(name: str = None):
    """
    Get a logger instance with optional name binding.
    
    Args:
        name: Optional name to bind to the logger
        
    Returns:
        Logger instance
    """
    if name:
        return logger.bind(module=name)
    return logger

