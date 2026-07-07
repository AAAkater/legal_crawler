"""Logging configuration via loguru.

Importing this module configures loguru sinks globally — no function
call needed.  Just ``from legal_crawler.utils import logger`` (or
import this module once at startup) and logging is ready.
"""

import sys

from loguru import logger

# Configure sinks at import time.
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
