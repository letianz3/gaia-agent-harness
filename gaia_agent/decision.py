"""Answer selection, separated from confidence reporting.

Verification decides how much an answer is supported; it must not by itself
turn a plausible answer into a non-answer. Under exact-match scoring an
abstention scores the same as a wrong answer, while hiding which candidate the
evidence favoured. So unresolved verification is recorded (the run status is
INCOMPLETE and the trace names the reason), and the answer is the candidate
the structured checks favour, with the incumbent winning ties. Setting
AGENT_ABSTAIN_ON_UNVERIFIED=true restores strict abstention.
"""
import re

UNVERIFIED = 'Unable to verify answer'
CHECK_SCORES = {'PASS': 1, 'UNCERTAIN': 0, 'FAIL': -2}
_ABSTENTION = re.compile(
    r'^\s*(?:unable to|cannot|could not|i (?:cannot|can\'t|could not|do not know)|unknown\b|n/?a\b|none found'
    r'|not (?:found|available|determinable|enough|sufficient|verifiable)'
    r'|no (?:verifiable |reliable |direct |sufficient |available )?(?:information|evidence|data|answer|record)s?\b'
    r'|insufficient\b|there is no (?:verifiable |direct |available )?(?:information|evidence|data)'
    r'|(?:the )?(?:answer|information) (?:is |was )?(?:not available|unavailable|cannot be determined)'
    r'|no(?:ne| \w+(?: \w+)?) (?:is|was|are|were) (?:mentioned|found|listed|given|named|provided|identified)\b'
    r'|(?:it is |it was )?not (?:mentioned|listed|named|given|identified)\b)', re.I)


def is_abstention(answer):
    return not str(answer or '').strip() or bool(_ABSTENTION.match(str(answer)))


def candidate_score(row):
    checks = row.get('checks') if isinstance(row, dict) else None
    if not isinstance(checks, dict):
        return 0
    return sum(CHECK_SCORES.get(value, 0) for value in checks.values())


def unresolved(agent, trace, reason, incumbent, challenger=None, report=None):
    """Record unresolved verification and return the best-supported candidate."""
    trace.add('answer_verification_unresolved', reason=reason)
    if getattr(getattr(agent, 'settings', None), 'abstain_on_unverified', False):
        return UNVERIFIED
    candidates = [('A', incumbent)] + ([('B', challenger)] if challenger is not None else [])
    candidates = [(key, value) for key, value in candidates if not is_abstention(value)]
    if len(candidates) == 2 and ungrounded_incumbent(trace) and grounded(candidates[1][1], trace.events):
        candidates = candidates[1:]  # a fabricated incumbent cannot win a tie against a grounded challenger
    if not candidates:
        trace.add('best_effort_selection', selected=None, reason='no non-abstaining candidate')
        return UNVERIFIED
    rows = {r.get('id'): r for r in (report or {}).get('candidates', []) if isinstance(r, dict)}
    scores = {key: candidate_score(rows.get(key)) for key, _ in candidates}
    # max() keeps the first maximum: the incumbent wins ties.
    key, value = max(candidates, key=lambda item: scores[item[0]])
    trace.add('best_effort_selection', selected=key, answer=value, scores=scores,
              scope='unverified; selected by structured check scores, incumbent on ties')
    return value


_SENTENCES = re.compile(r'[a-z]{3,}[.!?]["\')\]]?\s+[A-Z]')  # "Mt. Rainier" is not two sentences
_PROSE_OPENING = re.compile(r'^(?:the|there|it|this|i|based|according|after|unfortunately|no)\b', re.I)


def looks_like_prose(answer):
    """Sentence structure, not length: long comma lists are legitimate submissions."""
    text = str(answer or '').strip()
    words = len(text.split())
    return ('\n' in text or bool(_SENTENCES.search(text))
            or (words >= 8 and bool(_PROSE_OPENING.match(text)) and text.endswith(('.', '!'))))


def submission_value(agent, question, candidate, trace, role):
    """Reduce a prose candidate to the value it commits to, or to an abstention.

    The extracted value must occur in the candidate text (extraction, not new
    reasoning). Text that says the answer is unavailable or does not exist
    becomes UNVERIFIED, so it can never outrank a concrete candidate.
    """
    if is_abstention(candidate) or not looks_like_prose(candidate):
        return candidate
    from .contracts import ask_json
    from .contracts import normalize_text
    report = ask_json(agent, 'A research step answered an exact-match question in prose. Return JSON '
                      '{"answer": "the exact submission value the text commits to, in the format the question '
                      'requests" or null}. Use null if the text says the answer cannot be determined, is '
                      'unavailable, or that the thing asked about does not exist. Copy the value from the '
                      'text; do not add facts.\nQuestion: ' + question + '\nText: ' + candidate, trace)
    value = report.get('answer')
    accepted = isinstance(value, str) and value.strip() and normalize_text(value) in normalize_text(candidate)
    result = value.strip() if accepted else UNVERIFIED
    trace.add('submission_form', role=role, original=candidate[:2000], value=result,
              scope='form only; extracted value must occur in the candidate text')
    return result


def executed_values(trace):
    """Outputs of successful code executions; a value computed by running code
    outranks the same model's unexecuted reasoning about the same data."""
    values = set()
    for event in trace.events:
        if (event.get('type') == 'tool_call' and event.get('name') == 'run_python' and event.get('succeeded')
                and not str(event.get('result', '')).startswith('(completed with no output')):
            lines = [line.strip() for line in str(event.get('result', '')).strip().splitlines() if line.strip()]
            if lines:
                values.add(_value_key(lines[-1]))
    return values


def _value_key(text):
    return ' '.join(re.sub(r'\s*,\s*', ', ', str(text).strip().strip('.')).split()).casefold()


def execution_backed(candidate, trace):
    return _value_key(candidate) in executed_values(trace)


def _canonical(text):
    import unicodedata
    return ' '.join(unicodedata.normalize('NFKC', str(text)).split()).casefold()


def grounded(value, events):
    """Whether a textual answer can be traced to inputs available when it was produced.

    Sources: the task input, successful tool results (search snippets included:
    this is provenance, not truth) and worker results. Purely numeric answers
    are often computed, so they are not judged here. List answers need every item.
    """
    text = str(value or '').strip()
    if not re.search(r'[^\W\d_]', text):
        return True
    items = [i.strip() for i in text.split(',')] if ',' in text else [text]
    parts = []
    for event in events:
        if event.get('type') == 'input_evidence' or event.get('type') == 'subtask_result' or (
                event.get('type') == 'tool_call' and event.get('succeeded')):
            parts.append(str(event.get('result', '')))
    corpus = _canonical('\n'.join(parts))
    return all(_canonical(item) in corpus for item in items if item)


def ungrounded_incumbent(trace):
    """Recorded at the start of verification, before verification fetches anything."""
    record = next((e for e in trace.events if e.get('type') == 'answer_grounding'), None)
    return record is not None and record.get('grounded') is False
