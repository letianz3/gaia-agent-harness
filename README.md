---
title: GAIA Agent Harness Final Project
emoji: 🕵️
colorFrom: indigo
colorTo: blue
sdk: static
app_file: index.html
pinned: false
---

# GAIA Agent Harness — Final Project

Standalone educational tool-using agent with configurable memory, planning,
verification and multi-agent execution. See [evaluation and failure analysis](EVALUATION.md)
and [provenance](ATTRIBUTION.md). Credentials, benchmark data, raw traces and
downloaded engines are excluded from Git.

This project composes Modules 0–11 around the Hugging Face Final Assignment adapter. Features remain configurable; `02f_run_all_modules.bat` enables the full stack. Course Module 12 is a production roadmap, not an implemented production-readiness claim.

## Evaluation iterations

Versions below track the same 20-question development set, not course-module
numbers. R0 is the basic full-harness version, not the earlier Modules 0–3-only
agent. It already includes the GAIA adapter and basic task-facing tools. Every
row is a complete fresh run submitted to the official scorer;
failed experiments are retained in Git, without mixing answers across runs.

| Version / runtime commit | Score | Chat tokens | Change and reason | Feedback |
|---|---:|---:|---|---|
| R0 · Base (archived source snapshot) | 11/20 | 346,674 | Compose the basic course-module implementations with the GAIA adapter and tools, before the subsequent GAIA-focused optimization rounds. | Starting full-harness baseline: modules were present, but retrieval, routing and evidence handling still caused failures. |
| R1 · `ea7a1dd` | 14/20 | 431,574 | Replace broad replanning with targeted evidence recovery and separate format repair. | Reference checkpoint; fewer unproductive model calls. |
| R2 · `25ac623` | 12/20 | 507,325 | Add completion contracts and visual reinspection to prevent missing evidence from becoming a factual premise. | Regression: overly strict unavailable answers; nested timestamps and illegal FEN bypassed reinspection. Not promoted. |
| R3 · `64f0b01` | 13/20 | 489,813 | Fix reinspection branches and relax the unavailable-answer policy. | Execution improved, but visual recognition and semantic classification remained wrong. Still below R1; restored R1. |
| R4 · `392ad9c` | 15/20 | 413,810 | Preserve recipe phrases as exact source spans; account for every list item, research technical definitions, and apply exclusions in code. | Recipe and botanical-list targets improved; unrelated spreadsheet and historical-nationality answers regressed. Classification was not yet stable. |
| R5 · `042b2e3` | **16/20** | **350,250** | Direct grid transcription still failed, so crop and label chessboard cells, identify pieces, map coordinates in code, then call the engine. | Chess repair reproduced in targeted and full tests. Recipe remained correct; botanical classification regressed. Current checkpoint. |

R5 uses **18.8% fewer chat tokens** than R1. The clearest reproduced repairs are
recipe wording and chess perception-to-engine execution. The actor answer also
became correct while a funding identifier regressed, giving **three gains minus
one regression = two net gains** over R1. Those unchanged web paths vary between
runs; this is not a controlled causal ablation or proof of generalization.

Remaining failures: video species distinctions, ambiguous botanical membership,
retrieving a paper's funding statement, and finding a complete historical roster.
R5 passes 56 local tests; tests validate execution contracts, not factual accuracy.
Token totals exclude audio transcription. R0 is preserved as a local source
snapshot. Stable tags preserve R1/R4/R5, and
experiment branches retain R2/R3. Raw traces and attachments remain local.
See the [per-question ledger](FAILURE_ANALYSIS.md) and [metrics](EVALUATION.md)
for diagnoses, rejected approaches, and proposed next fixes.

## Full harness

- Modules 0–3: reusable `BaselineAgent` tool loop and per-task registry.
- Module 4: per-loop bounded memory compression preserving task and complete tool transactions.
- Module 5/10: `orchestration.py` combines routing and planning in one model request. It validates task IDs, specialist names and acyclic dependencies. Ready DAG nodes run in bounded waves; dependent nodes receive predecessor results. Specialists are registered delegation tools, each with a fresh history and restricted tool set. A failed predecessor prevents dependent execution. Results are evidence, not guaranteed truth.
- Module 6: bounded tool failures and independent JSON-mode critique. Separate format/equivalence repair from factual verification; repair from existing evidence first, or acquire a concrete missing fact with at most three tool-loop turns. Malformed reviews do not restart research; unchanged candidates are not reviewed twice. A critic PASS is not a correctness guarantee.
- Module 7: bounded parallel read-only tool calls, serial unsafe/media calls, ordered results. Identical signatures stay serial so failure limits cannot be bypassed. Specialist waves and tool batches have separate concurrency caps (not a global provider RPM limiter).
- Module 8: JSON Schema validation, dangerous-tool metadata, default-deny approval callback and audit events. Applications may supply `registry.approval(name, arguments)` backed by a real human decision. No destructive demo tool is exposed to GAIA. Python AST restrictions plus a subprocess are not a security sandbox.
- Module 9: persistent traces, run outcomes, specialist identities, model request hashes and `python scripts/view_trace.py PATH` timeline viewer.
- Module 11: importable package, centralized configuration, per-task model response cache, content-addressed system-prompt versions, call budget, configurable chat-cost estimates. Zero configured pricing means unknown cost; transcription and third-party fees are excluded. Cache entries do not survive the task and cached responses are not billed twice.

`python scripts/run_full_experiment.py` runs exactly 20 fetched questions in a new directory under `.runs/full_TIMESTAMP`, copies only prior attachments, snapshots source files, then submits the answers to the official scorer. This command consumes model tokens and writes a leaderboard submission; it does not publish source code to the Space. `02f` runs the suite without submitting; use `04` for that workflow's cached answers.

All-module experiments use fresh external-tool caches. Historical runs used different prompts and cache states, so their scores are not controlled architecture comparisons. Do not use leaderboard probing to choose answers for a reported agent run.

Compare measured usage without model calls or benchmark labels:
`python scripts/compare_runs.py .runs/full_FIRST .runs/full_SECOND`.
Detailed experiments and limitations are retained in [EVALUATION.md](EVALUATION.md).

## What is implemented

- basic OpenAI-compatible Chat Completions tool loop with bounded turns
- transport-level LLM request retries (reliability only, not an agent recovery policy)
- real web search, page reading, and YouTube caption retrieval
- guarded calculation-oriented Python execution
- task-scoped attachment access for text, Python, CSV, PDF, DOCX, and XLSX
- image input and OpenAI audio transcription
- official `/questions`, `/random-question`, `/files/{task_id}`, and `/submit` flows
- per-task JSON traces containing latency, token counts, tool calls, and errors
- incremental answer caching, so an interrupted 20-question run still leaves evidence
- separate **run** and **submit** buttons to prevent accidental leaderboard submissions
- temperature-zero sampling (not guaranteed deterministic) plus persistent replay of identical read-only web tool observations within the selected run directory
- Module 4 memory compression that always preserves the original task, summarizes only older complete tool transactions, and keeps recent messages verbatim

The official grader compares answers case-insensitively after trimming outer whitespace. The system prompt therefore requires answer-only output, while `normalize_answer()` removes common wrapper text, duplicate lines, inconsistent comma spacing, and applies alphabetical ordering only when the question explicitly requests it.

## Experiment boundary

This project intentionally separates five layers:

- **Agent core:** basic loop, tool calling, and Tool Registry
- **External capabilities:** web/page search, Python, YouTube, and attachment readers
- **GAIA adapter:** questions, files, exact-match cleanup, and submission
- **Evaluation infrastructure:** traces, latency, token counts, and saved answers
- **Deployment:** Gradio, Hugging Face OAuth, and the local CLI

The original pre-memory run scored **10/20 (50%)**. Memory can be switched off with `AGENT_MEMORY_ENABLED=false`. Planning, recovery, parallel tools and multi-agent routing have separate feature flags; enable matching configurations when making comparisons. Historical best scores alone do not establish causal improvements.

## Local setup

From this directory:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `OPENAI_API_KEY` in your shell (the Python code deliberately does not auto-load secret files). To use the GAIA attachment fallback, first accept the dataset terms for `gaia-benchmark/GAIA`, then also set `HF_TOKEN`:

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:HF_TOKEN = "your-read-token"
python cli.py random
```

Other useful commands:

```powershell
python cli.py ask "What is 17 * 23? Return only the number."
python cli.py all
python app.py
pytest -q
```

For tests, install `requirements-dev.txt` first. For local chess analysis,
download Stockfish from its official distribution and set `STOCKFISH_PATH` to
the executable. A local Windows executable under `.tools/stockfish/` is also
detected. Without an engine, the tool attempts Lichess cloud evaluation; a cloud
cache miss is not a solved position. The engine does not validate image recognition.

The bundled Windows publishing/submission scripts retain the author's
`zzzt19/gaia-baseline-agent` Space settings. Change those settings to your own
account before publishing or submitting. A local run incurs provider usage;
submitting cached answers does not rerun the agent.

Artifacts are written to `.runs/`:

```text
.runs/
  answers.json
  experiments/
    <timestamp>_<label>/
      answers.json
      summary.json
      traces/
  <task-id>/
    files/
    tool_cache.json
    trace.json
```

## Deploy to Hugging Face Spaces

1. Create a public Static Space to host the source code, or use a Gradio Space if your account supports compute Spaces.
2. Copy the **contents of this directory** to the Space repository root.
3. For the free Static workflow, run and score locally; the Space is only the public source-code URL.
4. Upload with `03_publish_space.bat`, then submit locally with `04_submit_cached_answers.bat`.

The leaderboard expects a public `https://huggingface.co/spaces/<user>/<space>/tree/main` code URL. The Space runtime supplies `SPACE_ID`, which the app uses to build it.

### Current scoring-service caveat

During local verification on 2026-08-30, the official `/questions` and `/random-question` endpoints worked, but `/files/{task_id}` returned HTTP 404 for all five questions that advertised attachments. On a 404, the client now uses an authenticated fallback to the official gated `gaia-benchmark/GAIA` dataset. Accept that dataset's terms and provide `HF_TOKEN`; without a token, the question still runs without the unavailable attachment.

## Windows workflow scripts

- `00_hf_login_once.bat`: cache the fine-grained Hugging Face login locally.
- `00_save_openai_key_once.bat`: securely prompt once and persist `OPENAI_API_KEY` as a Windows user environment variable.
- `01_test_local.bat`: run Ruff and pytest without model API calls.
- `02_run_gaia_all.bat`: run all 20 questions, update `.runs/answers.json`, and archive an experiment snapshot (uses model tokens).
- `02a_run_stable_baseline.bat`: run the controlled agent with Memory disabled.
- `02b_run_module04_memory.bat`: run the same controlled agent with Module 4 Memory enabled.
- `03_publish_space.bat`: upload only source/configuration files to the public Static Space.
- `04_submit_cached_answers.bat`: submit the existing cached answers without rerunning the agent.

The scripts never store or upload secret values. Identical search, page, and YouTube-caption calls are cached per task to reduce external-result variance across module experiments.

## Security boundary

`run_python` rejects dangerous imports, common dynamic-execution builtins, dunder access, long programs, and runs in an isolated child process with a timeout. This is a useful educational guardrail, not a mathematically secure Python sandbox. Keep the Space scoped to the public GAIA benchmark and do not expose arbitrary anonymous prompts without stronger container isolation.

`fetch_url` also rejects private, loopback, and link-local destinations to reduce SSRF risk.

## Suggested experiment sequence

Keep the 20 questions fixed and record each version in source control:

1. Controlled baseline (`02a_run_stable_baseline.bat`)
2. Memory / context compression
3. Explicit planning before tool use
4. Reflection / answer critic
5. Safe parallel search/fetch calls
6. Specialized researcher / file analyst orchestration

Compare score, latency, input/output tokens, tool-call count, and failure categories from the saved traces. Do not optimize on hidden answers; improve the general mechanism and rerun the same harness.
