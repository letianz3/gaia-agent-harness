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
_ABSTENTION = re.compile(r'^\s*(?:unable to|cannot|could not|i (?:cannot|can\'t|could not)|unknown\b|not (?:found|available|determinable))', re.I)


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
