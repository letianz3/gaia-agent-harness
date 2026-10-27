"""Structured JSON traces and aggregate metrics for each benchmark task."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class Trace:
    task_id: str
    question: str
    started_at: float = field(default_factory=time.monotonic)
    events: list[dict[str, Any]] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, event_type: str, **data: Any) -> None:
        with self._lock:
            self.events.append(
                {
                    "type": event_type,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **data,
                }
            )

    def add_usage(self, usage: Any) -> None:
        if usage is None:
            return
        with self._lock:
            self.input_tokens += int(getattr(usage, "prompt_tokens", 0) or 0)
            self.output_tokens += int(getattr(usage, "completion_tokens", 0) or 0)

    def record_tool_call(self) -> None:
        with self._lock:
            self.tool_calls += 1

    def save(self, path: Path, answer: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            payload = {
                "task_id": self.task_id,
                "question": self.question,
                "answer": answer,
                "latency_seconds": round(time.monotonic() - self.started_at, 3),
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "tool_calls": self.tool_calls,
                "events": list(self.events),
            }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
