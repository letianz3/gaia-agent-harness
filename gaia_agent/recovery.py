"""Bounded tool-failure tracking and structured answer critique helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


def explicit_answer_violation(question: str, answer: str) -> str | None:
    """Find a task-contract violation visible without factual verification.

    This is deliberately narrow so recovery only triggers when the question and
    proposed answer prove the violation by themselves.
    """

    lowered = question.casefold()
    if any(
        phrase in lowered
        for phrase in (
            "without abbreviations",
            "without abbreviation",
            "do not abbreviate",
            "no abbreviations",
        )
    ):
        abbreviation = re.search(
            r"(?<!\w)(?:[A-Za-z]\.){2,}|(?<!\w)[A-Z][a-z]{0,3}\.(?=\s|$)",
            answer,
        )
        if abbreviation:
            return (
                "The task explicitly forbids abbreviations, but the answer contains "
                f"'{abbreviation.group(0)}'. Spell it out and re-check the exact answer."
            )

    return None


@dataclass
class FailureTracker:
    """Track repeated failures for the same tool call signature."""

    max_consecutive: int
    counts: dict[str, int] = field(default_factory=dict)

    @staticmethod
    def key(tool_name: str, arguments_json: str = "") -> str:
        try:
            arguments = json.loads(arguments_json or "{}")
            normalized = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
        except (ValueError, TypeError):
            normalized = arguments_json.strip()
        return f"{tool_name}:{normalized}"

    def record(self, tool_name: str, succeeded: bool, arguments_json: str = "") -> None:
        key = self.key(tool_name, arguments_json)
        self.counts[key] = 0 if succeeded else self.counts.get(key, 0) + 1

    def is_exhausted(self, tool_name: str, arguments_json: str = "") -> bool:
        return self.counts.get(self.key(tool_name, arguments_json), 0) >= self.max_consecutive

    def count(self, tool_name: str, arguments_json: str = "") -> int:
        return self.counts.get(self.key(tool_name, arguments_json), 0)


def parse_critique(raw: str) -> tuple[str, str, bool]:
    """Return (verdict, feedback, parse_failed); malformed critics are uncertain."""
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        value = json.loads(cleaned)
    except (ValueError, TypeError):
        return "UNCERTAIN", "", True
    if not isinstance(value, dict):
        return "UNCERTAIN", "", True
    verdict = str(value.get("verdict", "")).strip().upper()
    if verdict not in {"PASS", "FAIL", "UNCERTAIN"}:
        return "UNCERTAIN", "", True
    feedback = value.get("feedback", "")
    return verdict, str(feedback)[:2_000], False
