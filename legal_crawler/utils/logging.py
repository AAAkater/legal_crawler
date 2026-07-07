"""Logging configuration via loguru."""

import sys

from loguru import logger


def setup_logging() -> None:
    """Configure loguru sinks with a concise format.

    - stderr at INFO level for console feedback
    - ``crawler.log`` at DEBUG level with rotation and retention
    """
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <7}</level> | <cyan>{name}</cyan> - {message}",
    )
    logger.add(
        "crawler.log",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {name}:{function}:{line} - {message}",
    )
