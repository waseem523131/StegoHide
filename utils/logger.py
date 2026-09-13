"""Logging setup for the StegoHide application."""

import logging


def configure_logger(log_level="INFO"):
    """Configure the root logger used across the project."""
    level = getattr(logging, str(log_level).upper(), logging.INFO)
    logger = logging.getLogger("StegoHide")
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
        logger.addHandler(handler)

    logger.propagate = False
    return logger
