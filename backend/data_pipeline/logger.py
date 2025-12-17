"""
Pipeline Logger
===============
Centralized logging configuration for the data pipeline
"""

import logging
from pathlib import Path
from datetime import datetime


def setup_pipeline_logger(
    name: str = "pipeline",
    log_dir: str = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG
):
    """
    Setup a logger for the pipeline

    Args:
        name: Logger name
        log_dir: Directory to save log files (default: backend/logs/)
        console_level: Logging level for console output
        file_level: Logging level for file output

    Returns:
        Configured logger instance
    """
    if log_dir is None:
        log_dir = Path(__file__).parent.parent / "logs"

    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)  # Capture everything

    # Remove existing handlers (avoid duplicates)
    logger.handlers.clear()

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_formatter = logging.Formatter(
        '%(levelname)-8s | %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (DEBUG and above)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"pipeline_{timestamp}.log"

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(file_level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)-8s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    logger.info("=" * 70)
    logger.info(f"Pipeline Logger Initialized - {name}")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 70)

    return logger
