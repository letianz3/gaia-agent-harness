"""Compare trace costs without loading benchmark labels or calling a model."""
import argparse
from collections import Counter
import json
from pathlib import Path


def summarize(root):
    counts = Counter()
    traces = sorted(root.glob('*/trace.json'))
    for path in traces:
        events = json.loads(path.read_text(encoding='utf-8'))['events']
        first_review = next((i for i, e in enumerate(events) if e['type'] == 'critique'), len(events))
        for i, event in enumerate(events):
            kind = event['type']
            if kind == 'model_request':
                tokens = event['input_tokens'] + event['output_tokens']
                counts['model_calls'] += 1
                counts['total_chat_tokens'] += tokens
                counts['after_first_review_tokens' if i > first_review else 'through_first_review_tokens'] += tokens
            if kind == 'critique':
                counts['review_' + event['verdict']] += 1
                counts['parse_failures'] += bool(event.get('parse_failed'))
                counts['citation_failures'] += (bool(event.get('citation_failed')) or
                    event.get('feedback', '').startswith('No valid direct'))
            if kind in {'targeted_acquisition', 'evidence_repair', 'format_repair'}:
                counts[kind] += 1
            if kind == 'candidate_selection' and event.get('selected') == 'challenger':
                counts['selected_challengers'] += 1
                counts['selected_changed_answers'] += event.get('incumbent') != event.get('challenger')
    score = root / 'submission.json'
    return {'run': root.name, 'tasks': len(traces),
            'official_score': json.loads(score.read_text(encoding='utf-8')).get('score') if score.exists() else None,
            **counts}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs='+', type=Path)
    print(json.dumps([summarize(p) for p in parser.parse_args().runs], indent=2))
