"""Entry point for the legal crawler."""

import asyncio

from legal_crawler.pipeline import run_pipeline
from legal_crawler.utils import logger  # configures loguru sinks on import


async def main() -> None:
    """Run the crawler pipeline."""
    logger.info("Legal crawler starting up")
    await run_pipeline()


if __name__ == "__main__":
    asyncio.run(main())
