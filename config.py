"""Application configuration for the AI Coding Agent.

This module centralizes environment loading, repository paths, model settings,
and scanner limits so the rest of the agent can stay focused on its own
responsibility.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class AgentConfig:
    """Runtime settings required by the agent workflow."""

    project_root: Path = BASE_DIR
    target_repo: Path = BASE_DIR / "target_repo"
    logs_dir: Path = BASE_DIR / "logs"
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.6-flash"))
    max_file_size_bytes: int = field(
        default_factory=lambda: int(os.getenv("MAX_FILE_SIZE_BYTES", "120000"))
    )
    max_prompt_chars: int = field(
        default_factory=lambda: int(os.getenv("MAX_PROMPT_CHARS", "120000"))
    )

    ignored_directories: tuple[str, ...] = (
        "node_modules",
        ".git",
        "dist",
        "build",
        "coverage",
        "venv",
        "__pycache__",
    )

    preferred_files: tuple[str, ...] = (
        "README.md",
        "Readme.md",
        "package.json",
    )

    preferred_directories: tuple[str, ...] = (
        "routes",
        "controllers",
        "models",
        "services",
        "middlewares",
        "config",
    )

    def validate(self) -> None:
        """Fail early when required runtime configuration is missing."""

        if not self.target_repo.exists():
            raise FileNotFoundError(f"Target repository not found: {self.target_repo}")

        if not self.target_repo.is_dir():
            raise NotADirectoryError(f"Target repository is not a directory: {self.target_repo}")

        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is missing. Add it to .env before running the agent.")

        self.logs_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> AgentConfig:
    """Load environment variables and return validated application settings."""

    load_dotenv(BASE_DIR / ".env")
    config = AgentConfig()
    config.validate()
    return config
