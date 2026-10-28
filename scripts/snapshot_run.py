"""Archive answers, traces, and aggregate metrics for one experiment run."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gaia_agent.config import Settings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    args = parser.parse_args()
    label = re.sub(r"[^A-Za-z0-9_.-]+", "-", args.label).strip("-.") or "run"

    settings = Settings.from_env()
    answers_path = settings.runs_dir / "answers.json"
    answers = json.loads(answers_path.read_text(encoding="utf-8"))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = settings.runs_dir / "experiments" / f"{stamp}_{label}"
    traces_dir = destination / "traces"
    traces_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(answers_path, destination / "answers.json")

    traces = []
    for row in answers:
        source = settings.runs_dir / row["task_id"] / "trace.json"
        if source.exists():
            shutil.copy2(source, traces_dir / f"{row['task_id']}.json")
            traces.append(json.loads(source.read_text(encoding="utf-8")))

    summary = {
        "label": label,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "questions": len(answers),
        "model": settings.model,
        "typed_entities_enabled": settings.typed_entities_enabled,
        "temperature": settings.temperature,
        "memory_enabled": settings.memory_enabled,
        "memory_max_messages": settings.memory_max_messages,
        "memory_keep_recent": settings.memory_keep_recent,
        "planning_enabled": settings.planning_enabled,
        "planning_max_subtasks": settings.planning_max_subtasks,
        "planning_turns_per_subtask": settings.planning_turns_per_subtask,
        "recovery_enabled": settings.recovery_enabled,
        "max_consecutive_tool_failures": settings.max_consecutive_tool_failures,
        "max_reflection_rounds": settings.max_reflection_rounds,
        "replanning_enabled": settings.replanning_enabled,
        "max_replans": settings.max_replans,
        "parallel_tools_enabled": settings.parallel_tools_enabled,
        "max_parallel_tools": settings.max_parallel_tools,
        "multi_agent_enabled": settings.multi_agent_enabled,
        "llm_cache_enabled": settings.llm_cache_enabled,
        "max_llm_calls": settings.max_llm_calls,
        "input_price_per_million": settings.input_price_per_million,
        "output_price_per_million": settings.output_price_per_million,
        "specialist_runs": sum(e.get('type') == 'agent_started' for t in traces for e in t.get('events', [])),
        "model_requests": sum(e.get('type') == 'model_request' for t in traces for e in t.get('events', [])),
        "model_cache_hits": sum(e.get('type') == 'model_cache_hit' for t in traces for e in t.get('events', [])),
        "audit_events": sum(e.get('type') == 'audit' for t in traces for e in t.get('events', [])),
        "failed_tasks": sum(any(e.get('type') == 'run_finished' and e.get('status') in ('FAILED', 'BUDGET_STOP')
                                for e in t.get('events', [])) for t in traces),
        "input_tokens": sum(trace.get("input_tokens", 0) for trace in traces),
        "output_tokens": sum(trace.get("output_tokens", 0) for trace in traces),
        "latency_seconds": round(sum(trace.get("latency_seconds", 0) for trace in traces), 3),
        "tool_calls": sum(trace.get("tool_calls", 0) for trace in traces),
        "memory_compressions": sum(
            event.get("type") == "memory_compression"
            for trace in traces
            for event in trace.get("events", [])
        ),
        "plans": sum(
            event.get("type") == "planning"
            for trace in traces
            for event in trace.get("events", [])
        ),
        "planned_subtasks": sum(
            len(event.get("subtasks", []))
            for trace in traces
            for event in trace.get("events", [])
            if event.get("type") == "planning"
        ),
        "critic_calls": sum(
            event.get("type") == "critique"
            for trace in traces
            for event in trace.get("events", [])
        ),
        "critic_failures": sum(
            event.get("type") == "critique"
            and (
                event.get("verdict") == "FAIL"
                or ("verdict" not in event and not event.get("passes", True))
            )
            for trace in traces
            for event in trace.get("events", [])
        ),
        "critic_uncertain": sum(
            event.get("type") == "critique" and event.get("verdict") == "UNCERTAIN"
            for trace in traces
            for event in trace.get("events", [])
        ),
        "replans": sum(
            event.get("type") == "planning" and event.get("replan_round", 0) > 0
            for trace in traces
            for event in trace.get("events", [])
        ),
        "blocked_tool_calls": sum(
            event.get("type") == "tool_call" and event.get("blocked", False)
            for trace in traces
            for event in trace.get("events", [])
        ),
        "parallel_tool_batches": sum(
            event.get("type") == "tool_batch" and event.get("parallel", False)
            for trace in traces
            for event in trace.get("events", [])
        ),
        "parallel_tool_calls": sum(
            event.get("count", 0)
            for trace in traces
            for event in trace.get("events", [])
            if event.get("type") == "tool_batch" and event.get("parallel", False)
        ),
        "challengers_selected": sum(
            event.get("type") == "candidate_selection"
            and event.get("selected") == "challenger"
            for trace in traces
            for event in trace.get("events", [])
        ),
    }
    (destination / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    # Preserve exact code/config identity; do not copy secrets or runtime caches.
    import hashlib
    source_dir = destination / 'source'
    source_dir.mkdir()
    hashes = {}
    captured = settings.runs_dir / 'source'
    for path in (captured if captured.exists() else PROJECT_ROOT / 'gaia_agent').glob('*.py'):
        shutil.copy2(path, source_dir / path.name)
        hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    (destination / 'source_hashes.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    print(f"Experiment snapshot: {destination}")


if __name__ == "__main__":
    main()
