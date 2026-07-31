"""Planning logic for translating a product request into implementation intent.

The planner creates a structured execution plan from the repository summary and
the user request. It uses lightweight heuristics so the agent has a reliable
baseline even before asking the LLM for implementation details.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from explorer import RepositorySummary


FEATURE_INTENTS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("priority", "priorities", "importance", "urgent"), "Add note priority with low, medium, and high values"),
    (("archive", "archived", "unarchive"), "Add note archiving and archive filtering"),
    (("favorite", "favourite", "star", "pinned"), "Add favourite notes"),
    (("reminder", "remind", "due date", "due_date", "notify"), "Add note reminders"),
    (("share", "sharing", "shared"), "Add note sharing metadata"),
    (("recent", "recently edited", "last edited"), "Add recently edited notes support"),
    (("label", "labels"), "Add note labels"),
    (("category", "categories", "categorise", "categorize"), "Add note categories"),
    (("tag", "tags"), "Add note tags"),
    (("search", "find", "filter", "query"), "Add note search and filters"),
)


@dataclass(frozen=True)
class FileChangePlan:
    """Planned change for a single target repository file."""

    path: str
    reason: str
    risk: str = "Low"


@dataclass(frozen=True)
class ExecutionPlan:
    """Structured plan used by the LLM and final summarizer."""

    goal: str
    feature: str
    files_to_modify: tuple[FileChangePlan, ...]
    implementation_steps: tuple[str, ...]
    assumptions: tuple[str, ...] = field(default_factory=tuple)
    risks: tuple[str, ...] = field(default_factory=tuple)

    def as_prompt_context(self) -> str:
        """Render the execution plan as a stable text block for prompting."""

        lines = [
            f"Goal: {self.goal}",
            f"Feature: {self.feature}",
            "Files to modify:",
        ]

        for file_plan in self.files_to_modify:
            lines.append(f"- {file_plan.path}: {file_plan.reason} Risk: {file_plan.risk}")

        lines.append("Implementation steps:")
        lines.extend(f"- {step}" for step in self.implementation_steps)

        if self.assumptions:
            lines.append("Assumptions:")
            lines.extend(f"- {assumption}" for assumption in self.assumptions)

        if self.risks:
            lines.append("Risks:")
            lines.extend(f"- {risk}" for risk in self.risks)

        return "\n".join(lines)


class Planner:
    """Builds an implementation plan from repository context and user intent."""

    def create_plan(self, request: str, summary: RepositorySummary) -> ExecutionPlan:
        """Create a practical plan for the requested product improvement."""

        feature = self._choose_feature(request)
        files = self._select_files(summary, feature)

        return ExecutionPlan(
            goal=request.strip(),
            feature=feature,
            files_to_modify=tuple(files),
            implementation_steps=tuple(self._steps_for_feature(feature)),
            assumptions=(
                "The existing application behavior should remain backward compatible.",
                "The implementation should fit the current Node.js/Express/Mongoose style.",
                "The agent may create files only when the existing structure suggests doing so.",
            ),
            risks=(
                "Schema changes can affect existing notes if defaults are not handled carefully.",
                "Search behavior must avoid breaking the current list-notes endpoint.",
                "Generated changes should not introduce dependencies unless clearly necessary.",
            ),
        )

    @staticmethod
    def _choose_feature(request: str) -> str:
        """Infer the most useful feature bundle from a product request."""

        normalized = request.lower()
        matched_features = [
            feature
            for keywords, feature in FEATURE_INTENTS
            if any(keyword in normalized for keyword in keywords)
        ]

        wants_search = "Add note search and filters" in matched_features
        wants_organization = any(
            word in normalized
            for word in ("organise", "organize", "organization", "organisation", "categor")
        )
        organization_features = {
            "Add note tags",
            "Add note labels",
            "Add note categories",
        }
        matched_organization = [
            feature for feature in matched_features if feature in organization_features
        ]

        if wants_search and (matched_organization or wants_organization):
            return "Add note tags plus search and tag filters"
        if matched_features:
            return matched_features[0]
        if wants_organization:
            return "Add note organization metadata"

        return "Implement the smallest cohesive product improvement requested"

    @staticmethod
    def _select_files(summary: RepositorySummary, feature: str) -> list[FileChangePlan]:
        """Select likely files to edit based on repository layers."""

        plans: list[FileChangePlan] = []
        categories = summary.discovered_categories

        for path in categories.get("models", []):
            plans.append(
                FileChangePlan(
                    path=path,
                    reason=f"Extend persisted note data needed for: {feature}.",
                    risk="Medium",
                )
            )

        for path in categories.get("controllers", []):
            plans.append(
                FileChangePlan(
                    path=path,
                    reason=f"Implement request handling, query parsing, and business logic for: {feature}.",
                    risk="Medium",
                )
            )

        for path in categories.get("routes", []):
            plans.append(
                FileChangePlan(
                    path=path,
                    reason="Expose any new endpoint or document existing query parameters.",
                    risk="Low",
                )
            )

        if not plans:
            for repo_file in summary.files[:5]:
                plans.append(
                    FileChangePlan(
                        path=repo_file.relative_path,
                        reason="Relevant source file selected because no conventional app layers were found.",
                        risk="Medium",
                    )
                )

        return plans

    @staticmethod
    def _steps_for_feature(feature: str) -> list[str]:
        """Return implementation steps that stay reusable across request types."""

        return [
            "Inspect existing data model fields and endpoint contracts.",
            f"Apply the minimal model changes required to support: {feature}.",
            "Update controller logic while preserving existing create, read, update, and delete behavior.",
            "Adjust routes only if the feature requires a new endpoint or query pattern.",
            "Run syntax and consistency checks after file edits.",
            "Summarize changed files, assumptions, trade-offs, and future improvements.",
        ]
