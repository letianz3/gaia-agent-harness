"""Run selected development questions afresh; never read old answers into prompts."""
import argparse
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from gaia_agent import BaselineAgent,EvaluationRunner,Settings
from gaia_agent.evaluator import Question


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference',type=Path)
    parser.add_argument('prefixes',nargs='+')
    args=parser.parse_args()
    os.chdir(ROOT)
    for flag in ('MEMORY','PLANNING','RECOVERY','REPLANNING','PARALLEL_TOOLS','MULTI_AGENT','LLM_CACHE'):
        os.environ[f'AGENT_{flag}_ENABLED']='true'
    run=ROOT/'.runs'/('targeted_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    os.environ['AGENT_RUNS_DIR']=str(run)
    (run/'source').mkdir(parents=True)
    for path in (ROOT/'gaia_agent').glob('*.py'):shutil.copy2(path,run/'source'/path.name)
    (run/'version.json').write_text(json.dumps({'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()}),encoding='utf-8')
    questions=[]
    for prefix in args.prefixes:
        matches=list(args.reference.glob(prefix+'*/trace.json'))
        if len(matches)!=1:raise ValueError('prefix must identify one recorded question')
        source=matches[0]; record=json.loads(source.read_text(encoding='utf-8'))
        task=record['task_id']; dest=run/task/'files'; dest.mkdir(parents=True,exist_ok=True)
        if (source.parent/'files').exists():shutil.copytree(source.parent/'files',dest,dirs_exist_ok=True)
        questions.append(Question(task_id=task,question=record['question']))
    print('RUN_DIR='+str(run),flush=True)
    runner=EvaluationRunner(BaselineAgent(Settings.from_env()))
    print(json.dumps(runner.run(questions),ensure_ascii=False),flush=True)


if __name__=='__main__':main()
