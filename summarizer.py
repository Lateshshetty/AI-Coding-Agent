"""Final reporting for the AI Coding Agent.

The summarizer turns structured workflow outputs into a concise engineering
report covering what changed, why it changed, risks, assumptions, and follow-up
opportunities.
"""

from __future__ import annotations

from dataclasses import dataclass

from editor import AppliedChange
from explorer import RepositorySummary
from planner import ExecutionPlan
from verifier import VerificationResult


@dataclass(frozen=True)
class AgentRunSummary:
    """Human-readable summary of a completed agent run."""

    text: str


class Summarizer:
    """Creates the final report shown after the agent finishes."""

    def summarize(
        self,
        repository_summary: RepositorySummary,
        execution_plan: ExecutionPlan,
        changes: tuple[AppliedChange, ...],
        verification: VerificationResult,
    ) -> AgentRunSummary:
        """Build a professional run summary."""

        sections = [
            "# AI Coding Agent Summary",
            "",
            "## Repository Summary",
            self._repository_section(repository_summary),
            "",
            "## Execution Plan",
            execution_plan.as_prompt_context(),
            "",
            "## Modified Files",
            self._changes_section(changes),
            "",
            "## Reasons",
            self._reasons_section(execution_plan),
            "",
            "## Features Added",
            f"- {execution_plan.feature}",
            "",
            "## Assumptions",
            self._list_section(execution_plan.assumptions),
            "",
            "## Trade-offs",
            self._tradeoffs_section(execution_plan),
            "",
            "## Verification",
            self._verification_section(verification),
            "",
            "## Future Improvements",
            self._future_improvements_section(),
        ]

        return AgentRunSummary(text="\n".join(sections).strip() + "\n")

    @staticmethod
    def _repository_section(summary: RepositorySummary) -> str:
        """Summarize discovered repository structure."""

        lines = [f"- Root: {summary.root}"]
        for category, paths in sorted(summary.discovered_categories.items()):
            lines.append(f"- {category}: {len(paths)} file(s)")
        return "\n".join(lines)

    @staticmethod
    def _changes_section(changes: tuple[AppliedChange, ...]) -> str:
        """List created and updated files."""

        if not changes:
            return "- No file changes were applied."

        return "\n".join(
            f"- {change.relative_path}: {change.action}"
            for change in changes
        )

    @staticmethod
    def _reasons_section(plan: ExecutionPlan) -> str:
        """Explain why each planned file was selected."""

        if not plan.files_to_modify:
            return "- No specific files were planned."

        return "\n".join(
            f"- {file_plan.path}: {file_plan.reason}"
            for file_plan in plan.files_to_modify
        )

    @staticmethod
    def _tradeoffs_section(plan: ExecutionPlan) -> str:
        """Summarize known implementation trade-offs."""

        if not plan.risks:
            return "- No major trade-offs identified."

        return "\n".join(f"- {risk}" for risk in plan.risks)

    @staticmethod
    def _verification_section(result: VerificationResult) -> str:
        """Render verification checks, warnings, and errors."""

        lines = [f"- Passed: {result.passed}"]
        lines.extend(f"- Check: {check}" for check in result.checks)
        lines.extend(f"- Warning: {warning}" for warning in result.warnings)
        lines.extend(f"- Error: {error}" for error in result.errors)
        return "\n".join(lines)

    @staticmethod
    def _future_improvements_section() -> str:
        """List sensible follow-up enhancements for the agent."""

        return "\n".join(
            (
                "- Add automated unit test generation when the target repository has a test framework.",
                "- Support unified diff output in addition to complete-file replacement.",
                "- Add optional Git branch creation and commit generation for safer review workflows.",
                "- Add richer dependency analysis for larger applications.",
            )
        )

    @staticmethod
    def _list_section(items: tuple[str, ...]) -> str:
        """Render a tuple of text items as markdown bullets."""

        if not items:
            return "- None."

        return "\n".join(f"- {item}" for item in items)
