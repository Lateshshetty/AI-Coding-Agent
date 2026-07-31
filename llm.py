"""Gemini client and prompt construction for the AI Coding Agent.

The LLM module owns all interaction with Google's supported ``google-genai``
SDK. Other modules pass in structured repository context and receive an
implementation response that the editor can parse and apply.
"""

from __future__ import annotations

from dataclasses import dataclass

from google import genai

from config import AgentConfig
from explorer import RepositorySummary
from planner import ExecutionPlan


@dataclass(frozen=True)
class LLMImplementation:
    """Raw implementation response returned by the language model."""

    text: str


class GeminiClient:
    """Small wrapper around the Google Gemini API using the google-genai SDK."""

    def __init__(self, config: AgentConfig) -> None:
        self._config = config
        self._client = genai.Client(api_key=config.gemini_api_key)

    def generate_implementation(
        self,
        user_request: str,
        repository_summary: RepositorySummary,
        execution_plan: ExecutionPlan,
    ) -> LLMImplementation:
        """Ask Gemini to produce concrete file changes for the target repo."""

        prompt = self._build_implementation_prompt(
            user_request=user_request,
            repository_summary=repository_summary,
            execution_plan=execution_plan,
        )
        try:
            response = self._client.models.generate_content(
                model=self._config.gemini_model,
                contents=prompt,
            )
        except Exception as exc:
            raise RuntimeError(self._format_generation_error(exc)) from exc

        text = (getattr(response, "text", None) or "").strip()

        if not text:
            raise RuntimeError(
                "Gemini returned an empty implementation response. "
                "Check the prompt, model name, API key, and Google AI Studio quota."
            )

        return LLMImplementation(text=text)

    def _format_generation_error(self, exc: Exception) -> str:
        """Convert SDK/network failures into actionable operator messages."""

        message = str(exc)
        exception_name = exc.__class__.__name__
        normalized = message.lower()

        if "getaddrinfo failed" in normalized or "connecterror" in exception_name.lower():
            return (
                "Could not connect to Gemini. Check your internet connection, DNS, "
                "proxy/VPN settings, and whether Google AI Studio endpoints are reachable."
            )

        if "not_found" in normalized or "no longer available" in normalized:
            return (
                f"Gemini model '{self._config.gemini_model}' is unavailable for this API key. "
                "Update GEMINI_MODEL in .env to a currently supported Google AI Studio model."
            )

        if "api key" in normalized or "permission" in normalized or "unauthorized" in normalized:
            return (
                "Gemini authentication failed. Check GEMINI_API_KEY in .env and confirm the "
                "key is enabled for Google AI Studio."
            )

        return f"Gemini generation failed: {message}"

    def _build_implementation_prompt(
        self,
        user_request: str,
        repository_summary: RepositorySummary,
        execution_plan: ExecutionPlan,
    ) -> str:
        """Create a constrained prompt for safe, reviewable code generation."""

        repo_context = repository_summary.as_prompt_context()
        plan_context = execution_plan.as_prompt_context()

        if len(repo_context) > self._config.max_prompt_chars:
            repo_context = repo_context[: self._config.max_prompt_chars]

        return f"""
You are a senior software engineer modifying an existing target repository.

The AI Coding Agent itself is Python, but the target repository may use another
language. Do not rewrite the target application. Make the smallest cohesive
changes that implement the product request while preserving existing behavior.

User request:
{user_request}

Execution plan:
{plan_context}

Repository context:
{repo_context}

Return only file changes in this exact format:

BEGIN_FILE: relative/path/from/target_repo
```language
complete file content
```
END_FILE

Rules:
- Include complete content for every changed or created file.
- Use paths relative to target_repo.
- Do not include markdown explanation outside BEGIN_FILE blocks.
- Do not hardcode this one request into the agent architecture.
- Avoid new dependencies unless the existing application clearly needs them.
- Preserve formatting and conventions from the existing target repository.
""".strip()
