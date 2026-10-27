"""Client for the official question/file/submission endpoints."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import requests

from .agent import BaselineAgent
from .attachments import download_attachment
from .config import Settings


@dataclass(frozen=True)
class Question:
    task_id: str
    question: str
    level: str = "1"
    file_name: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Question:
        return cls(
            task_id=value["task_id"],
            question=value["question"],
            level=str(value.get("Level", value.get("level", "1"))),
            file_name=value.get("file_name") or "",
        )


class ScoringClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.from_env()

    def questions(self) -> list[Question]:
        response = requests.get(
            f"{self.settings.api_url}/questions", timeout=self.settings.request_timeout
        )
        response.raise_for_status()
        return [Question.from_dict(item) for item in response.json()]

    def random_question(self) -> Question:
        response = requests.get(
            f"{self.settings.api_url}/random-question",
            timeout=self.settings.request_timeout,
        )
        response.raise_for_status()
        return Question.from_dict(response.json())

    def submit(self, username: str, agent_code: str, answers: list[dict[str, str]]) -> dict[str, Any]:
        if not username.strip() or not agent_code.startswith("https://huggingface.co/spaces/"):
            raise ValueError("submission requires a Hugging Face username and public Space code URL")
        payload = {
            "username": username.strip(),
            "agent_code": agent_code,
            "answers": answers,
        }
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = requests.post(
                    f"{self.settings.api_url}/submit",
                    json=payload,
                    timeout=max(60, self.settings.request_timeout),
                )
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                last_error = exc
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if attempt == 2 or (status is not None and status < 500):
                    detail = getattr(getattr(exc, "response", None), "text", "")[:1_000]
                    raise RuntimeError(
                        f"GAIA submission failed after {attempt + 1} attempt(s): {exc}; "
                        f"response={detail!r}"
                    ) from exc
                time.sleep(2**attempt)
        raise RuntimeError(f"GAIA submission failed: {last_error}")


class EvaluationRunner:
    def __init__(
        self,
        agent: BaselineAgent,
        scoring: ScoringClient | None = None,
    ) -> None:
        self.agent = agent
        self.settings = agent.settings
        self.scoring = scoring or ScoringClient(self.settings)
        self.answers_path = self.settings.runs_dir / "answers.json"

    def run_question(self, item: Question) -> dict[str, str]:
        task_dir = self.settings.runs_dir / item.task_id / "files"
        download_attachment(
            self.settings.api_url,
            item.task_id,
            item.file_name,
            task_dir,
            timeout=self.settings.request_timeout,
        )
        answer = self.agent.answer(item.question, item.task_id, task_dir)
        return {
            "task_id": item.task_id,
            "question": item.question,
            "submitted_answer": answer,
        }

    def run(self, questions: Iterable[Question]) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        for item in questions:
            try:
                results.append(self.run_question(item))
            except Exception as exc:  # noqa: BLE001 - one task must not abort the benchmark run.
                results.append(
                    {
                        "task_id": item.task_id,
                        "question": item.question,
                        "submitted_answer": f"AGENT ERROR: {type(exc).__name__}: {exc}",
                    }
                )
            self._save(results)
        return results

    def _save(self, results: list[dict[str, str]]) -> None:
        self.answers_path.parent.mkdir(parents=True, exist_ok=True)
        self.answers_path.write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def load_answers(self) -> list[dict[str, str]]:
        if not self.answers_path.exists():
            return []
        return json.loads(self.answers_path.read_text(encoding="utf-8"))

    @staticmethod
    def submission_answers(results: list[dict[str, str]]) -> list[dict[str, str]]:
        return [
            {"task_id": row["task_id"], "submitted_answer": row["submitted_answer"]}
            for row in results
            if not row["submitted_answer"].startswith("AGENT ERROR:")
        ]
