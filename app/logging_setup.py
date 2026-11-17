"""Logging configuration for the application.

Attaches a stdout handler to the top-level ``app`` logger so our stage logs are
visible when running locally under uvicorn (whose default config does not
surface application INFO logs). ``propagate = False`` avoids duplicate lines.
"""

from __future__ import annotations

import logging
import sys

_configured = False


def configure_logging(level: str = "INFO") -> None:
    """Configure the ``app`` logger once per process."""
    global _configured
    if _configured:
        return

    logger = logging.getLogger("app")
    logger.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.propagate = False

    _configured = True
