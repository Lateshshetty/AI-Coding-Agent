"""Repository exploration for the AI Coding Agent.

The explorer walks the target repository, filters out generated or dependency
folders, reads relevant source files, and returns a compact summary that the
planner and LLM can reason about.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from config import AgentConfig


TEXT_EXTENSIONS = {
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".json",
    ".md",
    ".env",
    ".yml",
    ".yaml",
    ".html",
    ".css",
}


@dataclass(frozen=True)
class RepositoryFile:
    """A source file discovered inside the target repository."""

    path: Path
    relative_path: str
    content: str
    category: str


@dataclass(frozen=True)
class RepositorySummary:
    """Structured description of the target repository."""

    root: Path
    files: tuple[RepositoryFile, ...]
    package_metadata: str | None = None
    readme: str | None = None
    discovered_categories: dict[str, list[str]] = field(default_factory=dict)

    def as_prompt_context(self) -> str:
        """Render the repository summary into a prompt-friendly text block."""

        sections = [
            f"Repository root: {self.root}",
            "Discovered categories:",
        ]

        for category, paths in sorted(self.discovered_categories.items()):
            joined_paths = ", ".join(paths) if paths else "None"
            sections.append(f"- {category}: {joined_paths}")

        if self.package_metadata:
            sections.append("\npackage.json:\n" + self.package_metadata)

        if self.readme:
            sections.append("\nREADME:\n" + self.readme)

        sections.append("\nRelevant files:")
        for repo_file in self.files:
            sections.append(
                f"\n--- {repo_file.relative_path} ({repo_file.category}) ---\n"
                f"{repo_file.content}"
            )

        return "\n".join(sections)


class RepositoryExplorer:
    """Scans a repository and extracts the files most useful for code changes."""

    def __init__(self, config: AgentConfig) -> None:
        self._config = config

    def explore(self) -> RepositorySummary:
        """Walk the target repository and return a structured summary."""

        files: list[RepositoryFile] = []
        categories: dict[str, list[str]] = {}
        package_metadata: str | None = None
        readme: str | None = None

        for path in sorted(self._config.target_repo.rglob("*")):
            if not path.is_file() or self._should_ignore(path):
                continue

            relative_path = path.relative_to(self._config.target_repo).as_posix()
            category = self._categorize(path)
            content = self._read_text(path)

            if content is None:
                continue

            repo_file = RepositoryFile(
                path=path,
                relative_path=relative_path,
                content=content,
                category=category,
            )
            files.append(repo_file)
            categories.setdefault(category, []).append(relative_path)

            if path.name == "package.json":
                package_metadata = content
            elif path.name.lower() in {"readme.md", "readme"}:
                readme = content

        return RepositorySummary(
            root=self._config.target_repo,
            files=tuple(files),
            package_metadata=package_metadata,
            readme=readme,
            discovered_categories=categories,
        )

    def _should_ignore(self, path: Path) -> bool:
        """Return whether a file should be excluded from repository analysis."""

        relative_parts = path.relative_to(self._config.target_repo).parts
        if any(part in self._config.ignored_directories for part in relative_parts):
            return True

        if path.stat().st_size > self._config.max_file_size_bytes:
            return True

        return path.suffix.lower() not in TEXT_EXTENSIONS and path.name not in self._config.preferred_files

    def _categorize(self, path: Path) -> str:
        """Classify a source file by conventional application layer."""

        parts = {part.lower() for part in path.parts}
        file_name = path.name.lower()

        if file_name.startswith("readme"):
            return "readme"
        if file_name == "package.json":
            return "package"

        for directory in self._config.preferred_directories:
            if directory.lower() in parts:
                return directory

        if file_name.endswith(".routes.js") or "route" in file_name:
            return "routes"
        if file_name.endswith(".controller.js") or "controller" in file_name:
            return "controllers"
        if file_name.endswith(".model.js") or "model" in file_name:
            return "models"

        return "source"

    @staticmethod
    def _read_text(path: Path) -> str | None:
        """Read a text file while tolerating encoding differences."""

        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue

        return None
