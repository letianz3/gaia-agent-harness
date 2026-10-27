"""Gradio UI compatible with the Hugging Face Final Assignment Space."""

from __future__ import annotations

import os

import gradio as gr

from gaia_agent import BaselineAgent, EvaluationRunner, ScoringClient, Settings


def _rows(results: list[dict[str, str]]) -> list[list[str]]:
    return [[row["task_id"], row["question"], row["submitted_answer"]] for row in results]


def _runner() -> EvaluationRunner:
    settings = Settings.from_env()
    return EvaluationRunner(BaselineAgent(settings), ScoringClient(settings))


def run_random() -> tuple[str, list[list[str]]]:
    try:
        runner = _runner()
        result = runner.run([runner.scoring.random_question()])
        return "Random question completed. Inspect the answer and trace before submitting.", _rows(result)
    except Exception as exc:  # noqa: BLE001 - UI boundary must render failures, not crash.
        return f"Run failed: {type(exc).__name__}: {exc}", []


def run_all() -> tuple[str, list[list[str]]]:
    try:
        runner = _runner()
        results = runner.run(runner.scoring.questions())
        good = len(runner.submission_answers(results))
        return f"Completed {len(results)} questions; {good} answers are ready. Nothing was submitted yet.", _rows(results)
    except Exception as exc:  # noqa: BLE001 - UI boundary must render failures, not crash.
        return f"Run failed: {type(exc).__name__}: {exc}", []


def submit_cached(profile: gr.OAuthProfile | None) -> tuple[str, list[list[str]]]:
    if profile is None:
        return "Log in to Hugging Face before submitting.", []
    try:
        runner = _runner()
        results = runner.load_answers()
        answers = runner.submission_answers(results)
        if not answers:
            return "No cached answers found. Run the 20-question evaluation first.", []
        space_id = os.getenv("SPACE_ID", "")
        if not space_id:
            return "SPACE_ID is unavailable. Deploy this folder as a Hugging Face Space before submitting.", _rows(results)
        result = runner.scoring.submit(
            profile.username,
            f"https://huggingface.co/spaces/{space_id}/tree/main",
            answers,
        )
        status = (
            f"Submission successful: {result.get('score', 'N/A')}% "
            f"({result.get('correct_count', '?')}/{result.get('total_attempted', '?')})"
        )
        return status, _rows(results)
    except Exception as exc:  # noqa: BLE001 - UI boundary must render failures, not crash.
        return f"Submission failed: {type(exc).__name__}: {exc}", []


with gr.Blocks() as demo:
    gr.Markdown("# GAIA Agent Harness — Final Project")
    gr.Markdown(
        "Run one random question first. The full run caches answers and traces locally; "
        "submission is a separate explicit action. Add `OPENAI_API_KEY` in Space Secrets."
    )
    in_space = bool(os.getenv("SPACE_ID"))
    if in_space:
        gr.LoginButton()
    else:
        gr.Markdown("Local mode: leaderboard login and submission are available after deployment to a Space.")
    with gr.Row():
        random_button = gr.Button("Run 1 Random Question")
        all_button = gr.Button("Run All 20 (No Submit)", variant="primary")
        submit_button = gr.Button("Submit Cached Answers", interactive=in_space)
    status = gr.Textbox(label="Status", lines=4, interactive=False)
    table = gr.Dataframe(
        headers=["Task ID", "Question", "Submitted Answer"],
        datatype=["str", "str", "str"],
        label="Results",
        wrap=True,
    )
    random_button.click(run_random, outputs=[status, table])
    all_button.click(run_all, outputs=[status, table])
    if in_space:
        submit_button.click(submit_cached, outputs=[status, table])

demo.queue()


if __name__ == "__main__":
    demo.launch(debug=True, share=False)
