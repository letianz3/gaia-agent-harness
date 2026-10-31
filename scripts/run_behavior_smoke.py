"""Small non-GAIA behavioral smoke set; not a statistical generalization benchmark."""
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from gaia_agent import BaselineAgent,Settings

CASES=[
 ('arithmetic','Calculate 17 times 23. Return only the integer.','391'),
 ('version_order','As of 2018, our three software version numbers are 3, 4 and 5. What numbers are immediately before and after 4? Return only the two numbers separated by a comma. All facts are supplied; no web lookup is needed.','3, 5'),
 ('materials','Classify these items by the color written in their name.\n\nred cable, blue lid, red cap, green pen, blue mat\n\nReturn only red items, alphabetized in a comma separated list.','red cable, red cap'),
 ('culinary','A botanist is cooking, but this task uses culinary categories: tomatoes and cucumbers count as vegetables; milk, eggs, and sugar do not. Classify this list:\n\ntomatoes, milk, cucumbers, eggs, sugar\n\nGive just the culinary vegetables, alphabetized in a comma separated list.','cucumbers, tomatoes'),
 ('dated_reading','A report updated in 2025 contains this archive: in 2018 Delta had 14 members, and in 2019 it had 18. How many members did Delta have in 2018? Use only this supplied report. Return only the integer.','14'),
 ('explicit_exclusion','Classify these objects using the words in their labels:\n\nlarge metal box, small metal cup, small wooden tray, large wooden bowl, small metal lid\n\nSelect metal objects, excluding large objects. Alphabetize the result as a comma separated list.','small metal cup, small metal lid'),
]

def main():
 os.chdir(ROOT)
 for flag in ('MEMORY','PLANNING','RECOVERY','REPLANNING','PARALLEL_TOOLS','MULTI_AGENT','LLM_CACHE'):
  os.environ[f'AGENT_{flag}_ENABLED']='true'
 run=ROOT/'.runs'/('behavior_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
 os.environ['AGENT_RUNS_DIR']=str(run)
 agent=BaselineAgent(Settings.from_env())
 rows=[]
 for name,question,expected in CASES:
  answer=agent(question,task_id=name)
  rows.append(dict(name=name,answer=answer,expected=expected,passed=answer.strip().casefold()==expected.casefold()))
  print(json.dumps(rows[-1]),flush=True)
 (run/'behavior_results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
 print('RUN_DIR='+str(run),flush=True)
 print('PASS='+str(sum(r['passed'] for r in rows))+'/'+str(len(rows)),flush=True)

if __name__=='__main__':main()
