from __future__ import annotations

import logging
from typing import Final

from rich.logging import RichHandler

_LOG_FORMAT: Final[str] = "%(message)s"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Initialize logging with Rich and return the app logger."""
    logging.basicConfig(
        level=level,
        format=_LOG_FORMAT,
        datefmt="[%X]",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                show_time=True,
                show_level=True,
                show_path=False,
            )
        ],
        force=True,
    )

    logger = logging.getLogger("cleandesk")
    logger.setLevel(level)
    return logger
