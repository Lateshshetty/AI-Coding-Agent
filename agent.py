"""Command-line entry point for the AI Coding Agent.

This module orchestrates the full workflow: explore the target repository,
create an execution plan, ask Gemini for implementation changes, apply those
changes, verify the result, and print a concise engineering summary.
"""

from __future__ import annotations

import argparse
import sys

from rich.console import Console
from rich.panel import Panel

from config import load_config
from editor import CodeEditor
from explorer import RepositoryExplorer
from llm import GeminiClient
from logger import setup_logger
from planner import Planner
from summarizer import Summarizer
from verifier import Verifier


DEFAULT_REQUEST = "Improve the application so users can better organise and search their notes."


class AICodingAgent:
    """Coordinates repository analysis, planning, code generation, and verification."""

    def __init__(self, user_request: str = DEFAULT_REQUEST, verbose: bool = False) -> None:
        self._verbose = verbose
        self._config = load_config()
        self._logger = setup_logger(self._config.logs_dir, verbose=verbose)
        self._console = Console()
        self._user_request = user_request

        self._explorer = RepositoryExplorer(self._config)
        self._planner = Planner()
        self._llm = GeminiClient(self._config)
        self._editor = CodeEditor(self._config)
        self._verifier = Verifier(self._config)
        self._summarizer = Summarizer()

    def run(self) -> int:
        """Execute the complete agent workflow."""

        try:
            self._print_header()
            self._logger.info("Loading Repository...")
            repository_summary = self._explorer.explore()
            self._logger.info("Repository Loaded")

            self._logger.info("Scanning Files...")
            self._log_discovered_layers(repository_summary.discovered_categories)

            self._logger.info("Generating Repository Summary...")
            self._logger.info("Creating Execution Plan...")
            execution_plan = self._planner.create_plan(self._user_request, repository_summary)

            self._logger.info("Connecting to Gemini...")
            self._logger.info("Generating Implementation...")
            implementation = self._llm.generate_implementation(
                user_request=self._user_request,
                repository_summary=repository_summary,
                execution_plan=execution_plan,
            )

            self._logger.info("Applying Code Changes...")
            changes = self._editor.apply(implementation)

            self._logger.info("Running Verification...")
            verification = self._verifier.verify(changes)

            self._logger.info("Generating Summary...")
            run_summary = self._summarizer.summarize(
                repository_summary=repository_summary,
                execution_plan=execution_plan,
                changes=changes,
                verification=verification,
            )

            self._console.print(Panel(run_summary.text, title="Run Summary", expand=False))

            if verification.passed:
                self._logger.info("Completed Successfully.")
                return 0

            self._logger.error("Completed with verification errors.")
            return 1
        except Exception as exc:
            if self._verbose:
                self._logger.exception("Agent failed: %s", exc)
            else:
                self._logger.error("Agent failed: %s", exc)
            return 1

    def _print_header(self) -> None:
        """Display a clean workflow header."""

        self._console.print()
        self._console.rule("AI Coding Agent Started")

    def _log_discovered_layers(self, categories: dict[str, list[str]]) -> None:
        """Log the app layers found during exploration."""

        labels = {
            "controllers": "Found Controllers",
            "models": "Found Models",
            "routes": "Found Routes",
            "services": "Found Services",
            "middlewares": "Found Middlewares",
            "config": "Found Config",
        }

        for category, message in labels.items():
            if categories.get(category):
                self._logger.info(message)


def parse_args() -> argparse.Namespace:
    """Parse command-line options."""

    parser = argparse.ArgumentParser(description="Run the AI Coding Agent.")
    parser.add_argument(
        "--request",
        default=DEFAULT_REQUEST,
        help="Product request to implement in target_repo.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug-level console logging.",
    )
    return parser.parse_args()


def main() -> int:
    """Application entry point."""

    args = parse_args()
    agent = AICodingAgent(user_request=args.request, verbose=args.verbose)
    return agent.run()


if __name__ == "__main__":
    sys.exit(main())
