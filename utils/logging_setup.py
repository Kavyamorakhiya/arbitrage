# utils/logging_setup.py

import logging
import sys

def setup_logger(log_to_file=False, filename="arbitrage.log", logger_name="cex_dex_arbitrage"):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(stream_handler)

    if log_to_file:
        file_handler = logging.FileHandler(filename)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ))
        logger.addHandler(file_handler)

    return logger
