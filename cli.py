"""Local CLI for cheap one-question iteration before deploying the Space."""

from __future__ import annotations

import argparse
import json
import sys

from gaia_agent import BaselineAgent, EvaluationRunner, ScoringClient, Settings


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Run the GAIA Final Project agent")
    parser.add_argument("mode", choices=["random", "all", "ask"])
    parser.add_argument("question", nargs="?", help="question text for ask mode")
    args = parser.parse_args()

    settings = Settings.from_env()
    agent = BaselineAgent(settings)
    runner = EvaluationRunner(agent, ScoringClient(settings))
    if args.mode == "ask":
        if not args.question:
            parser.error("ask mode requires a question")
        print(agent(args.question))
        return
    questions = [runner.scoring.random_question()] if args.mode == "random" else runner.scoring.questions()
    print(json.dumps(runner.run(questions), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
