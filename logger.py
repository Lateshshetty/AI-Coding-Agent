"""Logging utilities for the AI Coding Agent.

The agent uses one shared logger so console output remains consistent while a
timestamped log file captures enough detail for debugging failed runs.
"""

from __future__ import annotations

import logging
from pathlib import Path

from rich.logging import RichHandler


LOGGER_NAME = "ai_coding_agent"


def setup_logger(logs_dir: Path, verbose: bool = False) -> logging.Logger:
    """Create and configure the application logger."""

    logs_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    console_handler = RichHandler(
        show_time=False,
        show_path=False,
        rich_tracebacks=True,
        markup=False,
    )
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    file_handler = logging.FileHandler(logs_dir / "agent.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


def get_logger() -> logging.Logger:
    """Return the configured agent logger."""

    return logging.getLogger(LOGGER_NAME)
