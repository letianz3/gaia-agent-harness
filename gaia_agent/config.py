"""Environment-driven configuration with no secrets committed to source."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


def _nonnegative_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {raw!r}") from exc
    if value < 0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _boolean(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false, got {raw!r}")


@dataclass(frozen=True)
class Settings:
    api_url: str
    api_key: str
    model: str
    base_url: str | None
    max_turns: int
    llm_retries: int
    search_results: int
    request_timeout: int
    runs_dir: Path
    temperature: float = 0.0
    memory_enabled: bool = True
    memory_max_messages: int = 16
    memory_keep_recent: int = 6
    planning_enabled: bool = False
    planning_max_subtasks: int = 4
    planning_turns_per_subtask: int = 6
    recovery_enabled: bool = False
    max_consecutive_tool_failures: int = 2
    max_reflection_rounds: int = 2
    replanning_enabled: bool = False
    max_replans: int = 1
    parallel_tools_enabled: bool = False
    max_parallel_tools: int = 3
    multi_agent_enabled: bool = False
    llm_cache_enabled: bool = False
    max_llm_calls: int = 100
    input_price_per_million: float = 0.0
    output_price_per_million: float = 0.0

    @classmethod
    def from_env(cls) -> Settings:
        memory_max_messages = _positive_int("AGENT_MEMORY_MAX_MESSAGES", 16)
        memory_keep_recent = _positive_int("AGENT_MEMORY_KEEP_RECENT", 6)
        if memory_keep_recent >= memory_max_messages:
            raise ValueError("AGENT_MEMORY_KEEP_RECENT must be smaller than AGENT_MEMORY_MAX_MESSAGES")
        return cls(
            api_url=os.getenv(
                "GAIA_API_URL", "https://agents-course-unit4-scoring.hf.space"
            ).rstrip("/"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            base_url=os.getenv("OPENAI_BASE_URL") or None,
            max_turns=_positive_int("AGENT_MAX_TURNS", 12),
            llm_retries=_positive_int("AGENT_LLM_RETRIES", 3),
            search_results=_positive_int("AGENT_SEARCH_RESULTS", 6),
            request_timeout=_positive_int("AGENT_REQUEST_TIMEOUT", 30),
            runs_dir=Path(os.getenv("AGENT_RUNS_DIR", ".runs")).resolve(),
            temperature=_nonnegative_float("AGENT_TEMPERATURE", 0.0),
            memory_enabled=_boolean("AGENT_MEMORY_ENABLED", True),
            memory_max_messages=memory_max_messages,
            memory_keep_recent=memory_keep_recent,
            planning_enabled=_boolean("AGENT_PLANNING_ENABLED", False),
            planning_max_subtasks=_positive_int("AGENT_PLANNING_MAX_SUBTASKS", 4),
            planning_turns_per_subtask=_positive_int(
                "AGENT_PLANNING_TURNS_PER_SUBTASK", 6
            ),
            recovery_enabled=_boolean("AGENT_RECOVERY_ENABLED", False),
            max_consecutive_tool_failures=_positive_int(
                "AGENT_MAX_CONSECUTIVE_TOOL_FAILURES", 2
            ),
            max_reflection_rounds=_positive_int("AGENT_MAX_REFLECTION_ROUNDS", 2),
            replanning_enabled=_boolean("AGENT_REPLANNING_ENABLED", False),
            max_replans=_positive_int("AGENT_MAX_REPLANS", 1),
            parallel_tools_enabled=_boolean("AGENT_PARALLEL_TOOLS_ENABLED", False),
            max_parallel_tools=_positive_int("AGENT_MAX_PARALLEL_TOOLS", 3),
            multi_agent_enabled=_boolean("AGENT_MULTI_AGENT_ENABLED", False),
            llm_cache_enabled=_boolean("AGENT_LLM_CACHE_ENABLED", False),
            max_llm_calls=_positive_int("AGENT_MAX_LLM_CALLS", 100),
            input_price_per_million=_nonnegative_float("AGENT_INPUT_PRICE_PER_MILLION", 0),
            output_price_per_million=_nonnegative_float("AGENT_OUTPUT_PRICE_PER_MILLION", 0),
        )
