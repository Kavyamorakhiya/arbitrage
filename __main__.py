import logging
from utils.logging_setup import setup_logger
setup_logger(log_to_file=True)
from bot import main
import asyncio
import asyncpg



logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.debug("This should appear in both terminal and file.")
    asyncio.run(main())
