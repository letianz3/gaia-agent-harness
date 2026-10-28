"""Bounded raw evidence for synthesis and independent verification."""
import json
import re


def read_json_object(raw):
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip(), flags=re.I)
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def evidence_packet(events, start_index=0, budget=8000):
    # Recent direct observations precede search snippets; never promote worker prose
    # or failed tool output into factual support.
    candidates = [(i, e) for i, e in enumerate(events)
                  if e.get('type') == 'input_evidence' or (i >= start_index
                  and e.get('type') == 'tool_call' and e.get('succeeded'))]
    candidates.sort(key=lambda x: (x[1].get('type') == 'input_evidence',
                                   x[1].get('name') != 'search_web', x[0]), reverse=True)
    selected, seen = [], set()
    for i, event in candidates:
        value = str(event.get('result', ''))
        if not value or value in seen:
            continue
        if value.startswith('(completed with no output'):
            continue
        seen.add(value)
        limit = 4000 if event.get('type') == 'input_evidence' else 1400
        excerpt = value if len(value) <= limit else value[:limit-600] + '\n[excerpt omitted]\n' + value[-600:]
        item = json.dumps({'id': f'E{i}', 'tool': event.get('name'),
                           'arguments': str(event.get('arguments', event.get('args', {})))[:300],
                           'kind': ('task_input' if event.get('type') == 'input_evidence' else
                                    'discovery_only' if event.get('name') == 'search_web' else 'observation'),
                           'excerpt': excerpt}, ensure_ascii=False)
        if sum(map(len, selected)) + len(item) + 1 <= budget:
            selected.append(item)
    return '\n'.join(selected)


def has_valid_support(raw, evidence):
    """Reject invented citations. This checks provenance, not factual entailment."""
    try:
        result = read_json_object(raw)
        records = {e['id']: e for e in map(json.loads, evidence.splitlines())}
        supports = result.get('support', [])
        return bool(supports) and all(
            isinstance(s, dict) and s.get('id') in records
            and records[s['id']]['kind'] in {'observation', 'task_input'}
            and len(s.get('quote', '').strip()) >= 3
            and s['quote'] in records[s['id']]['excerpt'] for s in supports)
    except (ValueError, TypeError, KeyError):
        return False
