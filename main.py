"""Entry point for the legal crawler."""

import asyncio

from loguru import logger

from legal_crawler.pipeline import run_pipeline
from legal_crawler.utils import setup_logging


async def main() -> None:
    """Run the crawler pipeline."""
    setup_logging()
    logger.info("Legal crawler starting up")
    await run_pipeline()


if __name__ == "__main__":
    asyncio.run(main())
