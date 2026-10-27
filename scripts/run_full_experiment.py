"""One isolated all-module GAIA experiment, with progress and official scoring."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from gaia_agent import BaselineAgent, EvaluationRunner, ScoringClient, Settings


def main():
    os.chdir(ROOT)
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    for name in ('MEMORY', 'PLANNING', 'RECOVERY', 'REPLANNING', 'PARALLEL_TOOLS', 'MULTI_AGENT', 'LLM_CACHE'):
        os.environ[f'AGENT_{name}_ENABLED'] = 'true'
    old_runs = Settings.from_env().runs_dir
    run_dir = old_runs / ('full_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    os.environ['AGENT_RUNS_DIR'] = str(run_dir)
    settings = Settings.from_env()
    (run_dir / 'source').mkdir(parents=True)
    for path in (ROOT / 'gaia_agent').glob('*.py'):
        shutil.copy2(path, run_dir / 'source' / path.name)
    scorer = ScoringClient(settings)
    questions = scorer.questions()
    if len(questions) != 20:
        raise RuntimeError(f'Expected 20 questions, got {len(questions)}')
    for q in questions:
        old_files = old_runs / q.task_id / 'files'
        if old_files.exists():
            shutil.copytree(old_files, run_dir / q.task_id / 'files')
    runner = EvaluationRunner(BaselineAgent(settings), scorer)
    print(f'RUN_DIR={run_dir}', flush=True)
    def progress():
        for index, q in enumerate(questions, 1):
            print(f'[{index}/20] {q.task_id}', flush=True)
            yield q
    results = runner.run(progress())
    subprocess.run([sys.executable, 'scripts/snapshot_run.py', 'all_modules'], check=True)
    answers = runner.submission_answers(results)
    score = scorer.submit('zzzt19', 'https://huggingface.co/spaces/zzzt19/gaia-baseline-agent/tree/main', answers)
    (run_dir / 'submission.json').write_text(json.dumps(score, indent=2), encoding='utf-8')
    print(json.dumps(score), flush=True)
    print(f'Completed {len(answers)}/20 without runtime errors. Results: {run_dir}', flush=True)


if __name__ == '__main__':
    main()
