# -*- coding: utf-8 -*-
"""
Islamic Prayer Times Telegram Bot - Logger Configuration
=====================================================
Optimized logging with production/dev modes and automatic log rotation.

Optimizations:
- Production mode: ERROR level only (reduces I/O)
- Dev mode: DEBUG level for troubleshooting
- Automatic log rotation (prevents disk filling)
- No logging inside loops
- Thread-safe handlers

Version: 2.0.0 (Production Ready)
Author: Islamic Prayer Bot Team
License: MIT
"""
import logging
import logging.handlers
import sys
import os
from pathlib import Path
from config import (
    LOG_FILE,
    LOG_FORMAT_DETAILED,
    LOG_FORMAT_SIMPLE,
    LOG_DATE_FORMAT,
    LOG_MAX_BYTES,
    LOG_BACKUP_COUNT
)


class ConsoleFilter(logging.Filter):
    """
    Custom filter to reduce noise in terminal.
    - Production: Only ERROR, CRITICAL
    - Dev: INFO, WARNING, ERROR, CRITICAL
    - Hides DEBUG messages in terminal always
    """
    def __init__(self, production_mode=False):
        super().__init__()
        self.production_mode = production_mode

    def filter(self, record):
        # In production, show only errors
        if self.production_mode:
            return record.levelno >= logging.ERROR
        # In dev, show INFO and above
        return record.levelno >= logging.INFO


def setup_logging() -> logging.Logger:
    """
    Set up optimized logging system with file rotation and queue handlers.

    Features:
    - Rotating file handler (prevents disk overflow)
    - Console filtering (reduces noise)
    - Detailed logs in file
    - Simple logs in terminal

    Returns:
        logging.Logger: Configured logger instance
    """
    # Detect environment
    production_mode = os.getenv('ENV', 'development').lower() == 'production'

    # ============================================
    # 1. Set up Root Logger (base)
    # ============================================
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Allow all levels

    # Clear any existing handlers to avoid duplication
    if root_logger.handlers:
        root_logger.handlers.clear()

    # ============================================
    # 2. Set up rotating log file (with automatic rotation)
    # ============================================
    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )

    # In production, only log WARNING+ to file to reduce I/O
    if production_mode:
        file_handler.setLevel(logging.WARNING)
    else:
        file_handler.setLevel(logging.DEBUG)  # All details in dev

    # Detailed format with file and line info
    file_formatter = logging.Formatter(
        fmt=LOG_FORMAT_DETAILED,
        datefmt=LOG_DATE_FORMAT
    )
    file_handler.setFormatter(file_formatter)

    # ============================================
    # 3. Set up console for terminal (filtered)
    # ============================================
    console_handler = logging.StreamHandler(sys.stdout)

    # Add filter to console
    console_handler.addFilter(ConsoleFilter(production_mode=production_mode))

    # Simple format for terminal
    console_formatter = logging.Formatter(
        fmt=LOG_FORMAT_SIMPLE,
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)

    # ============================================
    # 4. Add handlers to root logger
    # ============================================
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # ============================================
    # 5. Set up application-specific logger
    # ============================================
    logger = logging.getLogger('IslamicPrayerBot')
    logger.setLevel(logging.DEBUG)

    # Prevent duplicate messages (root logger handles them)
    logger.propagate = True

    # Log initialization info
    mode_str = "PRODUCTION" if production_mode else "DEVELOPMENT"
    logger.info("=" * 60)
    logger.info(f"🚀 Logging system initialized in {mode_str} mode")
    if not production_mode:
        logger.info("📝 Debug logs enabled for development")
    else:
        logger.info("⚡ Production mode: only errors will be logged to console")
    logger.info(f"📂 Log file: {LOG_FILE}")
    logger.info(f"🔄 Log rotation: Max {LOG_MAX_BYTES/1024/1024:.1f}MB per file, keeping {LOG_BACKUP_COUNT} backups")
    logger.info("=" * 60)
    logger.debug("This is a DEBUG message - appears only in file and dev mode")
    logger.info("✅ Logging system ready for use")

    return logger


# Initialize logger on import
logger = setup_logging()
