"""Print the saved Module 9 execution timeline: python scripts/view_trace.py PATH."""
import json
import sys
from pathlib import Path

trace = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
for event in trace['events']:
    print(event.get('timestamp', ''), event['type'],
          event.get('agent_id', event.get('phase', '')), event.get('name', ''),
          event.get('status', event.get('verdict', '')), event.get('duration_ms', ''))
print('Answer:', trace['answer'])
print('Tokens:', trace['input_tokens'] + trace['output_tokens'], 'Latency:', trace['latency_seconds'])
