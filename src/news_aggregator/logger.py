"""Logging setup for the News Aggregator."""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logger(
    log_file: Path,
    name: str = "news_aggregator",
    level: int = logging.INFO,
    max_bytes: int = 50 * 1024 * 1024,  # 50MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up application logger with file and console handlers.

    Args:
        log_file: Path to the log file
        name: Logger name
        level: Logging level (default: INFO)
        max_bytes: Maximum log file size before rotation (default: 50MB)
        backup_count: Number of backup files to keep (default: 5)

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create log directory if it doesn't exist
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(detailed_formatter)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str = "news_aggregator") -> logging.Logger:
    """
    Get existing logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
