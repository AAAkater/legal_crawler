"""Entry point for the legal crawler."""

import asyncio


async def main() -> None:
    """Run the crawler pipeline."""
    print("Hello from legal-crawler!")


if __name__ == "__main__":
    asyncio.run(main())
