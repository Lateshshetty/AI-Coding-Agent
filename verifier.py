"""Verification checks for generated target repository changes.

The verifier performs lightweight, practical checks after editing: syntax,
imports/dependencies, duplicate file updates, and basic consistency. It is not a
replacement for a full test suite, but it catches common generation mistakes.
"""

from __future__ import annotations

import ast
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from config import AgentConfig
from editor import AppliedChange


@dataclass(frozen=True)
class VerificationResult:
    """Outcome of post-edit verification."""

    passed: bool
    checks: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)
    errors: tuple[str, ...] = field(default_factory=tuple)


class Verifier:
    """Runs consistency checks for the agent and modified target files."""

    def __init__(self, config: AgentConfig) -> None:
        self._config = config

    def verify(self, changes: tuple[AppliedChange, ...]) -> VerificationResult:
        """Run all verification checks and return a structured result."""

        checks: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []

        self._check_agent_python_syntax(checks, errors)
        self._check_duplicate_changes(changes, checks, errors)
        self._check_target_package_json(checks, warnings, errors)
        self._check_javascript_syntax(changes, checks, warnings, errors)

        return VerificationResult(
            passed=not errors,
            checks=tuple(checks),
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

    def _check_agent_python_syntax(self, checks: list[str], errors: list[str]) -> None:
        """Validate Python syntax for the agent modules."""

        python_files = [
            self._config.project_root / file_name
            for file_name in (
                "agent.py",
                "config.py",
                "logger.py",
                "explorer.py",
                "planner.py",
                "llm.py",
                "editor.py",
                "verifier.py",
                "summarizer.py",
                "utils.py",
            )
            if (self._config.project_root / file_name).exists()
        ]

        for path in python_files:
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                checks.append(f"Python syntax valid: {path.name}")
            except SyntaxError as exc:
                errors.append(f"Python syntax error in {path.name}: {exc}")

    @staticmethod
    def _check_duplicate_changes(
        changes: tuple[AppliedChange, ...],
        checks: list[str],
        errors: list[str],
    ) -> None:
        """Ensure no file was emitted more than once by the editor."""

        seen: set[str] = set()
        duplicates: set[str] = set()

        for change in changes:
            if change.relative_path in seen:
                duplicates.add(change.relative_path)
            seen.add(change.relative_path)

        if duplicates:
            errors.append("Duplicate file changes detected: " + ", ".join(sorted(duplicates)))
        else:
            checks.append("No duplicate file changes detected")

    def _check_target_package_json(
        self,
        checks: list[str],
        warnings: list[str],
        errors: list[str],
    ) -> None:
        """Verify package.json remains parseable when present."""

        package_path = self._config.target_repo / "package.json"
        if not package_path.exists():
            warnings.append("target_repo/package.json was not found")
            return

        try:
            package_data = json.loads(package_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid package.json: {exc}")
            return

        dependencies = package_data.get("dependencies", {})
        dev_dependencies = package_data.get("devDependencies", {})
        if isinstance(dependencies, dict) and isinstance(dev_dependencies, dict):
            checks.append("package.json dependencies are parseable")
        else:
            errors.append("package.json dependencies must be JSON objects when present")

    @staticmethod
    def _check_javascript_syntax(
        changes: tuple[AppliedChange, ...],
        checks: list[str],
        warnings: list[str],
        errors: list[str],
    ) -> None:
        """Run Node's syntax checker for modified JavaScript files if available."""

        js_files = [change.path for change in changes if change.path.suffix == ".js"]
        if not js_files:
            checks.append("No changed JavaScript files require syntax checking")
            return

        for path in js_files:
            try:
                result = subprocess.run(
                    ["node", "--check", str(path)],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=20,
                )
            except FileNotFoundError:
                warnings.append("Node.js is not available; skipped JavaScript syntax checks")
                return
            except subprocess.TimeoutExpired:
                errors.append(f"JavaScript syntax check timed out: {path.name}")
                continue

            if result.returncode == 0:
                checks.append(f"JavaScript syntax valid: {path.name}")
            else:
                output = (result.stderr or result.stdout).strip()
                errors.append(f"JavaScript syntax error in {path.name}: {output}")
