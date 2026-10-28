import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests
from openpyxl import Workbook

from gaia_agent.agent import BaselineAgent, normalize_answer, parse_plan
from gaia_agent.attachments import (
    download_attachment,
    read_attachment,
    resolve_task_file,
)
from gaia_agent.config import Settings
from gaia_agent.evaluator import ScoringClient
from gaia_agent.media_tools import (
    cloud_chess_analysis,
    extract_fen,
    sample_video_contact_sheets,
)
from gaia_agent.recovery import (
    FailureTracker,
    explicit_answer_violation,
    parse_critique,
)
from gaia_agent.registry import ToolRegistry
from gaia_agent.tools import _ExternalToolCache, run_python, youtube_transcript
from gaia_agent.tracing import Trace


def test_normalize_answer_removes_grader_noise() -> None:
    assert normalize_answer("FINAL ANSWER: 42\n") == "42"
    assert normalize_answer("The requested answer is: Wojciech") == "Wojciech"
    assert normalize_answer("```text\na, b\n```") == "a, b"
    assert normalize_answer("132,133\n132,133", "Return a comma-delimited list") == "132, 133"
    assert (
        normalize_answer("zucchini, broccoli, celery", "Alphabetize a comma separated list")
        == "broccoli, celery, zucchini"
    )


def test_plan_parser_validates_shape_limits_size_and_falls_back() -> None:
    assert parse_plan('```json\n["first", "second"]\n```', "whole task", 4) == [
        "first",
        "second",
    ]
    assert parse_plan('["one", "two", "three"]', "whole task", 2) == [
        "one",
        "two",
    ]
    assert parse_plan("not json", "whole task", 4) == ["whole task"]


def test_registry_turns_failures_into_observations() -> None:
    registry = ToolRegistry()
    registry.register(
        "double",
        "double a number",
        {"type": "object", "properties": {"value": {"type": "integer"}}},
        lambda value: str(value * 2),
    )
    assert registry.execute("double", '{"value": 4}') == ("8", True)
    result, ok = registry.execute("missing", "{}")
    assert not ok and result.startswith("ERROR:")


def test_failure_tracker_counts_consecutive_failures() -> None:
    tracker = FailureTracker(2)
    tracker.record("search", False, '{"query":"a"}')
    assert not tracker.is_exhausted("search", '{"query":"a"}')
    tracker.record("search", False, '{"query":"a"}')
    assert tracker.is_exhausted("search", '{"query":"a"}')
    assert not tracker.is_exhausted("search", '{"query":"b"}')
    tracker.record("search", True, '{"query":"a"}')
    assert tracker.count("search", '{"query":"a"}') == 0


def test_critique_parser_fails_open_on_invalid_output() -> None:
    assert parse_critique('{"verdict": "FAIL", "feedback": "wrong format"}') == (
        "FAIL",
        "wrong format",
        False,
    )
    assert parse_critique("not json") == ("UNCERTAIN", "", True)


def test_explicit_answer_violation_detects_forbidden_abbreviation() -> None:
    feedback = explicit_answer_violation(
        "Just give me the city name without abbreviations.", "St. Petersburg"
    )
    assert feedback is not None
    assert "St." in feedback
    assert explicit_answer_violation(
        "Just give me the city name without abbreviations.", "Saint Petersburg"
    ) is None


def test_python_tool_is_useful_but_blocks_os_access() -> None:
    assert run_python("print(sum(range(5)))") == "10"
    with pytest.raises(ValueError):
        run_python("import os\nprint(os.getcwd())")


def test_external_tool_cache_replays_identical_observations(tmp_path: Path) -> None:
    calls = 0

    def fetch(query: str) -> str:
        nonlocal calls
        calls += 1
        return f"result for {query}"

    cache_path = tmp_path / "tool_cache.json"
    first_cache = _ExternalToolCache(cache_path)
    assert first_cache.call("search", fetch, query="stable") == "result for stable"
    second_cache = _ExternalToolCache(cache_path)
    assert second_cache.call("search", fetch, query="stable") == "result for stable"
    assert calls == 1


def test_submission_retries_transient_server_error(tmp_path: Path, monkeypatch) -> None:
    calls = 0

    class FakeResponse:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code
            self.text = "temporary failure"

        def raise_for_status(self) -> None:
            if self.status_code >= 400:
                raise requests.HTTPError("server error", response=self)

        def json(self):
            return {"score": 55.0}

    def fake_post(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        return FakeResponse(500 if calls == 1 else 200)

    monkeypatch.setattr("gaia_agent.evaluator.requests.post", fake_post)
    monkeypatch.setattr("gaia_agent.evaluator.time.sleep", lambda _seconds: None)
    settings = Settings(
        api_url="https://example.test",
        api_key="",
        model="fake-model",
        base_url=None,
        max_turns=3,
        llm_retries=1,
        search_results=3,
        request_timeout=5,
        runs_dir=tmp_path / "runs",
    )
    result = ScoringClient(settings).submit(
        "user", "https://huggingface.co/spaces/user/agent", []
    )
    assert result == {"score": 55.0}
    assert calls == 2


def test_youtube_transcript_preserves_timestamps(monkeypatch) -> None:
    snippets = [
        SimpleNamespace(start=1.25, text="hello"),
        SimpleNamespace(start=4.0, text="world"),
    ]

    class FakeTranscriptApi:
        def fetch(self, _video_id: str):
            return snippets

    monkeypatch.setattr(
        "youtube_transcript_api.YouTubeTranscriptApi", FakeTranscriptApi
    )
    result = youtube_transcript("1htKBjuUWec")
    assert result == "[1.2s] hello\n[4.0s] world"


def test_video_sampler_creates_timestamped_contact_sheet(tmp_path: Path) -> None:
    import cv2
    import numpy as np
    from PIL import Image

    video_path = tmp_path / "sample.avi"
    writer = cv2.VideoWriter(
        str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 5.0, (64, 48)
    )
    assert writer.isOpened()
    for value in range(10):
        writer.write(np.full((48, 64, 3), value * 20, dtype=np.uint8))
    writer.release()

    sheets = sample_video_contact_sheets(
        video_path,
        tmp_path / "frames",
        timestamps_seconds=[0.2, 1.2],
        frame_count=2,
    )
    assert len(sheets) == 1
    with Image.open(sheets[0]) as image:
        assert image.size == (1500, 930)


def test_chess_fen_validation_and_cloud_move_conversion(monkeypatch) -> None:
    monkeypatch.delenv('STOCKFISH_PATH', raising=False)
    monkeypatch.setattr('shutil.which', lambda name: None)
    monkeypatch.setattr(Path, 'rglob', lambda self, pattern: iter(()))
    fen = extract_fen(
        "FEN: rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    )
    response = SimpleNamespace(
        status_code=200,
        json=lambda: {"pvs": [{"moves": "e2e4 e7e5", "cp": 20, "mate": None}]},
        raise_for_status=lambda: None,
    )
    monkeypatch.setattr("gaia_agent.media_tools.requests.get", lambda *_args, **_kwargs: response)
    result = cloud_chess_analysis(fen)
    assert "Best move: e4 (UCI e2e4)" in result


def test_attachment_reader_handles_text_and_xlsx(tmp_path: Path) -> None:
    text = tmp_path / "note.txt"
    text.write_text("hello", encoding="utf-8")
    assert read_attachment(text) == "hello"

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["item", "sales"])
    sheet.append(["burger", 12.5])
    xlsx = tmp_path / "sales.xlsx"
    workbook.save(xlsx)
    rendered = read_attachment(xlsx)
    assert "burger\t12.5" in rendered
    assert "sales\t12.5" in rendered


def test_missing_remote_attachment_does_not_abort_question(tmp_path: Path, monkeypatch) -> None:
    response = SimpleNamespace(status_code=404)
    monkeypatch.setattr("gaia_agent.attachments.requests.get", lambda *_args, **_kwargs: response)
    monkeypatch.setattr("gaia_agent.attachments.get_token", lambda: None)

    result = download_attachment(
        "https://example.test",
        "missing-task",
        "missing.pdf",
        tmp_path,
    )

    assert result is None
    assert list(tmp_path.iterdir()) == []


def test_missing_api_attachment_falls_back_to_gaia_dataset(tmp_path: Path, monkeypatch) -> None:
    response = SimpleNamespace(status_code=404)
    cached_file = tmp_path / "cached.py"
    cached_file.write_text("print(42)", encoding="utf-8")
    download_dir = tmp_path / "download"
    captured: dict[str, str] = {}

    def fake_hub_download(**kwargs) -> str:
        captured.update(kwargs)
        return str(cached_file)

    monkeypatch.setattr("gaia_agent.attachments.requests.get", lambda *_args, **_kwargs: response)
    monkeypatch.setattr("gaia_agent.attachments.get_token", lambda: "test-token")
    monkeypatch.setattr("gaia_agent.attachments.hf_hub_download", fake_hub_download)

    result = download_attachment(
        "https://example.test",
        "task-id",
        "task-id.py",
        download_dir,
    )

    assert result == download_dir / "task-id.py"
    assert result.read_text(encoding="utf-8") == "print(42)"
    assert captured["repo_id"] == "gaia-benchmark/GAIA"
    assert captured["filename"] == "2023/validation/task-id.py"


def test_file_resolution_stays_inside_task_directory(tmp_path: Path) -> None:
    (tmp_path / "ok.txt").write_text("ok", encoding="utf-8")
    assert resolve_task_file(tmp_path, "ok.txt").name == "ok.txt"
    with pytest.raises(ValueError):
        resolve_task_file(tmp_path, "../secret.txt")


def test_agent_completes_a_tool_calling_loop_and_saves_trace(tmp_path: Path) -> None:
    class FakeCompletions:
        def __init__(self) -> None:
            self.calls = 0

        def create(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                tool_call = SimpleNamespace(
                    id="call-1",
                    function=SimpleNamespace(name="run_python", arguments='{"code":"print(6 * 7)"}'),
                )
                message = SimpleNamespace(content=None, tool_calls=[tool_call])
            else:
                message = SimpleNamespace(content="FINAL ANSWER: 42", tool_calls=[])
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

    settings = Settings(
        api_url="https://example.test",
        api_key="",
        model="fake-model",
        base_url=None,
        max_turns=3,
        llm_retries=1,
        search_results=3,
        request_timeout=5,
        runs_dir=tmp_path / "runs",
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    task_dir = tmp_path / "files"
    task_dir.mkdir()

    answer = BaselineAgent(settings, client=client).answer("What is 6 * 7?", "task-1", task_dir)

    assert answer == "42"
    trace = (settings.runs_dir / "task-1" / "trace.json").read_text(encoding="utf-8")
    assert '"tool_calls": 1' in trace


def test_parallel_tool_calls_overlap_and_keep_message_order(tmp_path: Path) -> None:
    class ParallelCompletions:
        def __init__(self) -> None:
            self.calls = 0
            self.second_messages = []

        def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                tool_calls = [
                    SimpleNamespace(
                        id="call-one",
                        function=SimpleNamespace(
                            name="wait_tool", arguments='{"value":"one"}'
                        ),
                    ),
                    SimpleNamespace(
                        id="call-two",
                        function=SimpleNamespace(
                            name="wait_tool", arguments='{"value":"two"}'
                        ),
                    ),
                ]
                message = SimpleNamespace(content=None, tool_calls=tool_calls)
            else:
                self.second_messages = list(kwargs["messages"])
                message = SimpleNamespace(content="done", tool_calls=[])
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

    barrier = threading.Barrier(2)

    def wait_tool(value: str) -> str:
        barrier.wait(timeout=1)
        return value

    settings = Settings(
        api_url="https://example.test",
        api_key="",
        model="fake-model",
        base_url=None,
        max_turns=3,
        llm_retries=1,
        search_results=3,
        request_timeout=5,
        runs_dir=tmp_path / "runs",
        memory_enabled=False,
        parallel_tools_enabled=True,
        max_parallel_tools=2,
    )
    completions = ParallelCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    agent = BaselineAgent(settings, client=client)
    registry = ToolRegistry()
    registry.register(
        "wait_tool",
        "Wait for another call",
        {
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
        wait_tool,
        parallel_safe=True,
    )
    trace = Trace("parallel-task", "test")

    result = agent._run_tool_loop(
        [{"role": "system", "content": "system"}, {"role": "user", "content": "test"}],
        registry,
        trace,
        3,
        "agent",
    )

    assert result == "done"
    tool_messages = [
        message
        for message in completions.second_messages
        if isinstance(message, dict) and message.get("role") == "tool"
    ]
    assert [message["content"] for message in tool_messages] == ["one", "two"]
    batch = next(event for event in trace.events if event["type"] == "tool_batch")
    assert batch["parallel"] is True
    assert batch["count"] == 2
    assert batch["max_concurrency"] == 2


def test_planning_runs_isolated_subtasks_then_synthesizes(tmp_path: Path) -> None:
    class PlanningCompletions:
        def __init__(self) -> None:
            self.plain_calls = 0
            self.tool_calls = 0
            self.first_messages_by_subtask: list[list] = []

        def create(self, **kwargs):
            if "tools" not in kwargs:
                self.plain_calls += 1
                content = (
                    '["Calculate 6 * 7", "State the verified calculation result"]'
                    if self.plain_calls == 1
                    else "FINAL ANSWER: 42"
                )
                message = SimpleNamespace(content=content, tool_calls=[])
                return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

            self.tool_calls += 1
            if self.tool_calls in {1, 3}:
                self.first_messages_by_subtask.append(list(kwargs["messages"]))
            if self.tool_calls == 1:
                tool_call = SimpleNamespace(
                    id="planned-call",
                    function=SimpleNamespace(name="run_python", arguments='{"code":"print(6*7)"}'),
                )
                message = SimpleNamespace(content=None, tool_calls=[tool_call])
            elif self.tool_calls == 2:
                message = SimpleNamespace(content="The verified result is 42.", tool_calls=[])
            else:
                message = SimpleNamespace(content="Use the verified value 42.", tool_calls=[])
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

    settings = Settings(
        api_url="https://example.test",
        api_key="",
        model="fake-model",
        base_url=None,
        max_turns=4,
        llm_retries=1,
        search_results=3,
        request_timeout=5,
        runs_dir=tmp_path / "runs",
        memory_enabled=False,
        planning_enabled=True,
        planning_max_subtasks=4,
        planning_turns_per_subtask=3,
    )
    completions = PlanningCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    task_dir = tmp_path / "files"
    task_dir.mkdir()

    answer = BaselineAgent(settings, client=client).answer(
        "Calculate 6 * 7", "planning-task", task_dir
    )

    assert answer == "42"
    assert len(completions.first_messages_by_subtask) == 2
    assert all(len(messages) == 2 for messages in completions.first_messages_by_subtask)
    assert "Calculate 6 * 7" in completions.first_messages_by_subtask[0][1]["content"]
    assert "State the verified" in completions.first_messages_by_subtask[1][1]["content"]
    trace = json.loads(
        (settings.runs_dir / "planning-task" / "trace.json").read_text(encoding="utf-8")
    )
    event_types = [event["type"] for event in trace["events"]]
    assert event_types.count("planning") == 1
    assert event_types.count("subtask_result") == 2
    assert event_types.count("synthesis") == 1
    assert "memory_compression" not in event_types


def test_memory_compression_summarizes_old_complete_tool_transactions(tmp_path: Path) -> None:
    class MemoryCompletions:
        def __init__(self) -> None:
            self.main_calls = 0
            self.summary_calls = 0
            self.last_main_messages = []

        def create(self, **kwargs):
            if "tools" not in kwargs:
                self.summary_calls += 1
                message = SimpleNamespace(content="Earlier calculation result was 2.")
                return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

            self.main_calls += 1
            self.last_main_messages = kwargs["messages"]
            if self.main_calls <= 2:
                tool_call = SimpleNamespace(
                    id=f"call-{self.main_calls}",
                    function=SimpleNamespace(name="run_python", arguments='{"code":"print(1 + 1)"}'),
                )
                message = SimpleNamespace(role="assistant", content=None, tool_calls=[tool_call])
            else:
                message = SimpleNamespace(role="assistant", content="2", tool_calls=[])
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

    settings = Settings(
        api_url="https://example.test",
        api_key="",
        model="fake-model",
        base_url=None,
        max_turns=4,
        llm_retries=1,
        search_results=3,
        request_timeout=5,
        runs_dir=tmp_path / "runs",
        memory_max_messages=4,
        memory_keep_recent=2,
    )
    completions = MemoryCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    task_dir = tmp_path / "files"
    task_dir.mkdir()

    answer = BaselineAgent(settings, client=client).answer("Calculate twice", "memory-task", task_dir)

    assert answer == "2"
    assert completions.summary_calls == 1
    assert completions.last_main_messages[1]["role"] == "user"
    assert completions.last_main_messages[2]["content"].startswith("[MEMORY SUMMARY]")
    trace = json.loads(
        (settings.runs_dir / "memory-task" / "trace.json").read_text(encoding="utf-8")
    )
    assert any(event["type"] == "memory_compression" for event in trace["events"])


def test_memory_safe_cut_keeps_parallel_tool_transactions_whole() -> None:
    calls = [
        SimpleNamespace(id="call-a", function=SimpleNamespace(name="first")),
        SimpleNamespace(id="call-b", function=SimpleNamespace(name="second")),
    ]
    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "task"},
        SimpleNamespace(role="assistant", content=None, tool_calls=calls),
        {"role": "tool", "tool_call_id": "call-a", "content": "a"},
        {"role": "tool", "tool_call_id": "call-b", "content": "b"},
        {"role": "user", "content": "recent"},
        {"role": "assistant", "content": "recent answer"},
    ]

    assert BaselineAgent._safe_cut_index(messages, keep_recent=2) == 4


def test_baseline_has_no_tool_failure_recovery_policy(tmp_path: Path) -> None:
    class RepeatedFailureCompletions:
        def __init__(self) -> None:
            self.calls = 0

        def create(self, **_kwargs):
            self.calls += 1
            if self.calls <= 3:
                tool_call = SimpleNamespace(
                    id=f"call-{self.calls}",
                    function=SimpleNamespace(name="missing_tool", arguments="{}"),
                )
                message = SimpleNamespace(content=None, tool_calls=[tool_call])
            else:
                message = SimpleNamespace(content="best effort", tool_calls=[])
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

    settings = Settings(
        api_url="https://example.test",
        api_key="",
        model="fake-model",
        base_url=None,
        max_turns=5,
        llm_retries=1,
        search_results=3,
        request_timeout=5,
        runs_dir=tmp_path / "runs",
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=RepeatedFailureCompletions()))
    task_dir = tmp_path / "files"
    task_dir.mkdir()

    answer = BaselineAgent(settings, client=client).answer("Use a missing tool", "task-2", task_dir)

    assert answer == "best effort"
    trace = json.loads(
        (settings.runs_dir / "task-2" / "trace.json").read_text(encoding="utf-8")
    )
    tool_events = [event for event in trace["events"] if event["type"] == "tool_call"]
    assert len(tool_events) == 3
    assert all(event["result"].startswith("ERROR: unknown tool") for event in tool_events)


def test_recovery_blocks_tool_after_consecutive_failures(tmp_path: Path) -> None:
    class RepeatedCalls:
        def __init__(self) -> None:
            self.calls = 0

        def create(self, **_kwargs):
            self.calls += 1
            if self.calls <= 3:
                call = SimpleNamespace(
                    id=f"call-{self.calls}",
                    function=SimpleNamespace(name="always_fail", arguments="{}"),
                )
                message = SimpleNamespace(content=None, tool_calls=[call])
            else:
                message = SimpleNamespace(content="done", tool_calls=[])
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

    actual_calls = 0

    def always_fail() -> str:
        nonlocal actual_calls
        actual_calls += 1
        raise RuntimeError("failure")

    settings = Settings(
        api_url="https://example.test",
        api_key="",
        model="fake-model",
        base_url=None,
        max_turns=4,
        llm_retries=1,
        search_results=3,
        request_timeout=5,
        runs_dir=tmp_path / "runs",
        memory_enabled=False,
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=RepeatedCalls()))
    agent = BaselineAgent(settings, client=client)
    registry = ToolRegistry()
    registry.register(
        "always_fail",
        "always fails",
        {"type": "object", "properties": {}},
        always_fail,
    )
    trace = Trace("failure-task", "test")
    result = agent._run_tool_loop(
        [{"role": "user", "content": "test"}],
        registry,
        trace,
        4,
        "agent",
        failure_tracker=FailureTracker(2),
    )
    assert result == "done"
    assert actual_calls == 2
    assert sum(event.get("blocked", False) for event in trace.events) == 1


def test_targeted_recovery_rejects_unsupported_challenger(tmp_path: Path) -> None:
    class RecoveryCompletions:
        def __init__(self) -> None:
            self.plain_outputs = iter(
                [
                    '["Find the answer"]',
                    "wrong",
                    '{"verdict": "FAIL", "feedback": "The value is incorrect.", "next_action":"acquire_evidence", "target":"Use Python to recalculate the product."}',
                    '{"verdict": "PASS", "feedback": ""}',
                ]
            )
            self.subtask_outputs = iter(["Evidence suggests wrong.", "42"])

        def create(self, **kwargs):
            content = (
                next(self.subtask_outputs)
                if "tools" in kwargs
                else next(self.plain_outputs)
            )
            message = SimpleNamespace(content=content, tool_calls=[])
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

    settings = Settings(
        api_url="https://example.test",
        api_key="",
        model="fake-model",
        base_url=None,
        max_turns=4,
        llm_retries=1,
        search_results=3,
        request_timeout=5,
        runs_dir=tmp_path / "runs",
        memory_enabled=False,
        planning_enabled=True,
        recovery_enabled=True,
        replanning_enabled=True,
        max_replans=1,
        max_reflection_rounds=2,
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=RecoveryCompletions()))
    task_dir = tmp_path / "files"
    task_dir.mkdir()

    answer = BaselineAgent(settings, client=client).answer(
        "What is 6 * 7?", "replan-task", task_dir
    )
    # The fake solver provides prose only, no tool observation. A critic's bare
    # PASS cannot authorize replacing the incumbent under the evidence contract.
    assert answer == "wrong"
    trace = json.loads(
        (settings.runs_dir / "replan-task" / "trace.json").read_text(encoding="utf-8")
    )
    plans = [event for event in trace["events"] if event["type"] == "planning"]
    critiques = [event for event in trace["events"] if event["type"] == "critique"]
    assert [event["replan_round"] for event in plans] == [0]
    assert sum(e['type'] == 'targeted_acquisition' for e in trace['events']) == 1
    assert [event["passes"] for event in critiques] == [False, False]
    selection = next(
        event for event in trace["events"] if event["type"] == "candidate_selection"
    )
    assert selection["selected"] == "incumbent"


def test_uncertain_challenger_preserves_incumbent(tmp_path: Path) -> None:
    class ConservativeCompletions:
        def __init__(self) -> None:
            self.plain_outputs = iter(
                [
                    '["Find the answer"]',
                    "original",
                    '{"verdict": "FAIL", "feedback": "Concrete conflict.", "next_action":"acquire_evidence", "target":"Fetch the original source to resolve the conflict."}',
                    '{"verdict": "UNCERTAIN", "feedback": "Evidence is insufficient."}',
                ]
            )
            self.subtask_outputs = iter(["Initial evidence.", "challenger"])

        def create(self, **kwargs):
            content = (
                next(self.subtask_outputs)
                if "tools" in kwargs
                else next(self.plain_outputs)
            )
            message = SimpleNamespace(content=content, tool_calls=[])
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

    settings = Settings(
        api_url="https://example.test",
        api_key="",
        model="fake-model",
        base_url=None,
        max_turns=4,
        llm_retries=1,
        search_results=3,
        request_timeout=5,
        runs_dir=tmp_path / "runs",
        memory_enabled=False,
        planning_enabled=True,
        recovery_enabled=True,
        replanning_enabled=True,
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=ConservativeCompletions()))
    task_dir = tmp_path / "files"
    task_dir.mkdir()

    answer = BaselineAgent(settings, client=client).answer(
        "Find a value", "conservative-task", task_dir
    )
    assert answer == "original"
    trace = json.loads(
        (settings.runs_dir / "conservative-task" / "trace.json").read_text(
            encoding="utf-8"
        )
    )
    selection = next(
        event for event in trace["events"] if event["type"] == "candidate_selection"
    )
    assert selection["selected"] == "incumbent"
    assert selection["reason"] == "challenger_uncertain"
