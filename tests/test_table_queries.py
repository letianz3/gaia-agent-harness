import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from bs4 import BeautifulSoup

from gaia_agent.decision import UNVERIFIED, is_abstention, unresolved
from gaia_agent.table_queries import agrees, computed_answer, execute_query, observed_tables
from gaia_agent.tracing import Trace
from gaia_agent.web_tables import render_tables

QUESTION = ("What country had the least number of athletes at the 1928 Summer Olympics? If there's a tie "
            "for a number of athletes, return the first in alphabetical order. Give the IOC country code as your answer.")
SPEC = {'applicable': True, 'table_id': 'T1', 'operation': 'min', 'entity_column': 0, 'value_column': 51,
        'answer_column': 0, 'filters': [], 'tie_break': 'alphabetical', 'tie_break_column': 0,
        'basis': 'Total all column of the athlete count table'}


def page_event(html, url='https://example.org/page'):
    soup = BeautifulSoup(html, 'html.parser')
    render_tables(soup)
    body = '\n'.join(line.strip() for line in soup.get_text('\n').splitlines() if line.strip())
    return dict(type='tool_call', name='fetch_url', succeeded=True, result='SOURCE: ' + url + '\n' + body)


def count_page_event():
    return page_event((Path(__file__).parent / 'fixtures' / 'olympic_counts_table.html').read_text(encoding='utf-8'))


def scripted(*replies):
    queue = iter(replies)
    return lambda *a, **k: SimpleNamespace(usage=None, choices=[SimpleNamespace(
        message=SimpleNamespace(content=json.dumps(next(queue))))])


def table(event):
    [t] = observed_tables([event])
    return t


def test_extremum_and_alphabetical_tie_over_whole_table():
    result = execute_query(table(count_page_event()), SPEC)
    assert result['answer'] == 'CUB' and result['value'] == '1' and result['tied'] == ['CUB', 'PAN']
    assert result['excluded_aggregate_rows'] == 2  # blank-label total rows


def test_tie_without_a_stated_rule_is_not_silently_broken():
    with pytest.raises(ValueError, match='no tie rule'):
        execute_query(table(count_page_event()), dict(SPEC, tie_break='none'))


def test_count_with_inclusive_year_filter_and_rowspan_years():
    html = ('<table><tr><th>Year</th><th>Album</th><th>Type</th></tr>'
            '<tr><td>1999</td><td>A</td><td>Studio</td></tr>'
            '<tr><td>2005</td><td>B</td><td>Studio</td></tr>'
            '<tr><td rowspan="2">2009</td><td>C</td><td>Studio</td></tr><tr><td>D</td><td>Studio</td></tr>'
            '<tr><td>2008</td><td>E</td><td>Live</td></tr><tr><td>2011</td><td>F</td><td>Studio</td></tr></table>')
    spec = {'operation': 'count', 'entity_column': 1, 'filters': [
        {'column': 0, 'op': 'between', 'value': '2000', 'value2': '2009', 'question_span': 'between 2000 and 2009 (included)'},
        {'column': 2, 'op': 'eq', 'value': 'Studio', 'question_span': 'studio albums'}]}
    assert execute_query(table(page_event(html)), spec)['answer'] == '3'
    with pytest.raises(ValueError, match='question_span'):
        execute_query(table(page_event(html)), {'operation': 'count', 'entity_column': 1,
                                                'filters': [{'column': 2, 'op': 'eq', 'value': 'Studio'}]})


def test_value_lookup_requires_exactly_one_matching_row():
    html = '<table><tr><th>No.</th><th>Name</th></tr><tr><td>18</td><td>A</td></tr><tr><td>19</td><td>B</td></tr></table>'
    spec = {'operation': 'value', 'entity_column': 1, 'answer_column': 1,
            'filters': [{'column': 0, 'op': 'eq', 'value': '19', 'question_span': 'number 19'}]}
    assert execute_query(table(page_event(html)), spec)['answer'] == 'B'
    with pytest.raises(ValueError, match='exactly one'):
        execute_query(table(page_event(html)), dict(spec, filters=[]))


def test_bad_columns_are_rejected_not_guessed():
    t = table(count_page_event())
    with pytest.raises(ValueError, match='not numeric'):
        execute_query(t, dict(SPEC, value_column=2))
    with pytest.raises(ValueError, match='column index'):
        execute_query(t, dict(SPEC, value_column=99))


def test_numeric_incumbent_never_agrees_through_an_unrelated_cell():
    computed = {'answer': 'CUB', 'result': execute_query(table(count_page_event()), SPEC)}
    assert agrees('CUB', computed) and agrees('cub', computed)
    assert not agrees('1', computed) and not agrees('DEN', computed)


def test_not_applicable_or_incomplete_tables_change_nothing():
    trace = Trace('t', QUESTION)
    trace.events.append(count_page_event())
    agent = SimpleNamespace(_plain_completion=scripted({'applicable': False, 'reason': 'prose question'}))
    assert computed_answer(agent, QUESTION, trace) is None
    trace = Trace('t', QUESTION)
    event = count_page_event()
    event['result'] = event['result'].replace('| PAN |', '[Middle omitted; original passages follow]\n| PAN |')
    trace.events.append(event)
    assert observed_tables(trace.events) == []


def make_agent(monkeypatch, *replies):
    from gaia_agent.agent import BaselineAgent
    agent = object.__new__(BaselineAgent)
    agent.settings = SimpleNamespace(max_reflection_rounds=2, specialized_workflows_enabled=True)
    monkeypatch.setattr(agent, '_plain_completion', scripted(*replies))
    return agent


def test_agreement_settles_without_critic_and_review(monkeypatch):
    agent = make_agent(monkeypatch, SPEC)
    monkeypatch.setattr(agent, '_critique_answer', lambda *a: pytest.fail('critic not needed'))
    trace = Trace('t', QUESTION)
    trace.events.append(count_page_event())
    assert agent._recover_answer(QUESTION, QUESTION, 'CUB', None, trace, None, '') == 'CUB'


def test_reviewed_query_overrides_solver_but_failed_review_does_not(monkeypatch):
    """Replays R13 run 2 (solver/challenger DEN against a correct minimum of CUB)."""
    agent = make_agent(monkeypatch, SPEC, {'verdict': 'PASS', 'problems': []})
    monkeypatch.setattr(agent, '_critique_answer', lambda *a: pytest.fail('critic not needed'))
    trace = Trace('t', QUESTION)
    trace.events.append(count_page_event())
    assert agent._recover_answer(QUESTION, QUESTION, 'DEN', None, trace, None, '') == 'CUB'

    agent = make_agent(monkeypatch, SPEC, {'verdict': 'FAIL', 'problems': ['wrong edition']})
    critiques = []
    def critique(*args):
        critiques.append(args)
        return 'PASS', 'supported'
    monkeypatch.setattr(agent, '_critique_answer', critique)
    trace = Trace('t', QUESTION)
    trace.events.append(count_page_event())
    assert agent._recover_answer(QUESTION, QUESTION, 'DEN', None, trace, None, '') == 'DEN'
    assert critiques and any(e['type'] == 'table_query_unadopted' for e in trace.events)


def test_unresolved_selection_prefers_supported_non_abstaining_candidates():
    trace = Trace('t', 'q')
    agent = SimpleNamespace(settings=SimpleNamespace(abstain_on_unverified=False))
    report = {'candidates': [
        {'id': 'A', 'checks': {'task_constraints': 'PASS', 'source_identity': 'PASS', 'answer_value': 'FAIL'}},
        {'id': 'B', 'checks': {'task_constraints': 'PASS', 'source_identity': 'PASS', 'answer_value': 'UNCERTAIN'}}]}
    assert unresolved(agent, trace, 'r', 'X', 'Y', report) == 'Y'
    assert unresolved(agent, trace, 'r', 'X', 'Y', None) == 'X'  # tie: incumbent
    assert unresolved(agent, trace, 'r', 'Unable to verify historical roster', 'Y', None) == 'Y'
    assert unresolved(SimpleNamespace(settings=SimpleNamespace(abstain_on_unverified=True)), trace, 'r', 'X') == UNVERIFIED
    assert sum(e['type'] == 'answer_verification_unresolved' for e in trace.events) == 4
    assert is_abstention('Unable to verify answer') and not is_abstention('Uehara')
