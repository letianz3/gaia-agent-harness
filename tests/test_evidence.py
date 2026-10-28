import json
from types import SimpleNamespace
import pytest
from gaia_agent.evidence import evidence_packet, has_valid_support
from gaia_agent.tools import search_web, fetch_url


def test_recent_observation_survives_search_noise_and_worker_claims():
    events = [dict(type='tool_call', name='search_web', succeeded=True, result='noise'+str(i)*2000) for i in range(20)]
    events += [dict(type='subtask_result', result='fabricated answer'),
               dict(type='tool_call', name='fetch_url', succeeded=False, result='blocked'),
               dict(type='tool_call', name='read_file', succeeded=True, result='verified total 123')]
    packet = evidence_packet(events, budget=3000)
    assert 'verified total 123' in packet
    assert 'fabricated answer' not in packet and 'blocked' not in packet
    assert has_valid_support(json.dumps({'support':[{'id':'E22','quote':'total 123'}]}), packet)
    assert not has_valid_support(json.dumps({'support':[{'id':'E22','quote':'total 456'}]}), packet)
    assert not has_valid_support('{"verdict":"PASS"}', packet)


def test_search_uses_bounded_fallback(monkeypatch):
    import ddgs
    backends = []
    def text(self, query, **kw):
        backends.append(kw['backend'])
        if len(backends) == 1:
            raise RuntimeError('unavailable')
        return [{'title':'source','href':'https://example.org','body':'text'}]
    monkeypatch.setattr(ddgs, 'DDGS', lambda **kw: SimpleNamespace(text=lambda query, **kw: text(None, query, **kw)))
    assert 'example.org' in search_web('query', 3)
    assert backends == ['auto', 'bing']


def test_input_transcript_survives_replan_and_empty_python_is_not_evidence():
    events = [dict(type='input_evidence', name='original_task_and_transcripts',
                   result='Transcript: freshly peeled apples'),
              dict(type='tool_call', name='run_python', succeeded=True,
                   result='(completed with no output; use print() to return a result)')]
    packet = evidence_packet(events, start_index=1)
    assert 'freshly peeled apples' in packet
    assert 'completed with no output' not in packet
    assert has_valid_support(json.dumps({'support':[{'id':'E0','quote':'freshly peeled apples'}]}), packet)


def test_fetch_rejects_challenge_and_private_redirect(monkeypatch):
    import gaia_agent.tools as tools
    monkeypatch.setattr(tools, '_validate_public_url', lambda u: u if u.startswith('https://example.org') else (_ for _ in ()).throw(ValueError('private')))
    response = SimpleNamespace(is_redirect=False, iter_content=lambda **kw:iter([b'Verify you are human']), close=lambda:None, raise_for_status=lambda:None)
    monkeypatch.setattr(tools.requests, 'get', lambda *a, **k: response)
    with pytest.raises(ValueError, match='challenge'):
        fetch_url('https://example.org')
    response.is_redirect = True
    response.headers = {'Location':'http://127.0.0.1/'}
    with pytest.raises(ValueError, match='private'):
        fetch_url('https://example.org')


@pytest.mark.parametrize('review,expected', [('PASS', 'supported'), ('UNCERTAIN', 'original')])
def test_uncertainty_allows_one_acquisition_and_requires_review(monkeypatch, review, expected):
    from gaia_agent.agent import BaselineAgent
    from gaia_agent.tracing import Trace
    agent = object.__new__(BaselineAgent)
    agent.settings = SimpleNamespace(planning_enabled=True, replanning_enabled=True,
                                     max_reflection_rounds=2, max_replans=1, planning_turns_per_subtask=6)
    verdicts = iter([('UNCERTAIN', 'missing source'), (review, 'reviewed')])
    acquisitions = []
    def critique(*args):
        args[3].add('critique', next_action='acquire_evidence', target='Fetch the official page for the missing value')
        return next(verdicts)
    monkeypatch.setattr(agent, '_critique_answer', critique)
    def acquire(*args):
        acquisitions.append(True)
        return 'supported'
    monkeypatch.setattr(agent, '_revise_answer', acquire)
    assert agent._recover_answer('task', 'task', 'original', None, Trace('id', 'task'), None, '') == expected
    assert len(acquisitions) == 1


@pytest.mark.parametrize('problem', ['parse_failed', 'citation_failed'])
def test_broken_review_never_launches_more_research(monkeypatch, problem):
    from gaia_agent.agent import BaselineAgent
    from gaia_agent.tracing import Trace
    agent = object.__new__(BaselineAgent)
    agent.settings = SimpleNamespace(max_reflection_rounds=2)
    def review(*args):
        args[3].add('critique', next_action='acquire_evidence', target='Fetch a source', **{problem:True})
        return 'UNCERTAIN', 'review broken'
    monkeypatch.setattr(agent, '_critique_answer', review)
    assert agent._recover_answer('task', 'task', 'original', None, Trace('id','task'), None, '') == 'original'


def test_format_repair_is_separate_from_factual_review(monkeypatch):
    from gaia_agent.agent import BaselineAgent
    from gaia_agent.tracing import Trace
    agent = object.__new__(BaselineAgent)
    agent.settings = SimpleNamespace(max_reflection_rounds=2)
    replies = iter(['{"answer":"Mount Rainier"}', '{"equivalent":true,"format_ok":true}'])
    def complete(*args, **kwargs):
        assert kwargs['response_format'] == {'type':'json_object'}
        return SimpleNamespace(usage=None, choices=[SimpleNamespace(message=SimpleNamespace(content=next(replies)))])
    monkeypatch.setattr(agent, '_plain_completion', complete)
    trace = Trace('id', 'Return a mountain name without abbreviations')
    assert agent._recover_answer(trace.question, '', 'Mt. Rainier', None, trace, None, '') == 'Mount Rainier'
    assert trace.events[-1]['verification_scope'].startswith('format and equivalence only')


def test_fenced_json_support_and_non_object_responses():
    evidence = '{"id":"E0","kind":"observation","excerpt":"observed green leaves"}'
    assert has_valid_support('```json\n{"support":[{"id":"E0","quote":"green leaves"}]}\n```', evidence)
    assert not has_valid_support('[]', evidence)


def test_download_budget_uses_pdf_signature_and_stops_early(monkeypatch):
    import gaia_agent.tools as t
    monkeypatch.setattr(t,'HTML_DOWNLOAD_LIMIT',10)
    monkeypatch.setattr(t,'PDF_DOWNLOAD_LIMIT',30)
    pdf=SimpleNamespace(iter_content=lambda **kw:iter([b'%P',b'DF-',b'x'*20]))
    assert len(t.bounded_response_body(pdf))==25
    read=[]
    def chunks(**kw):
        for part in [b'<html>',b'x'*10,b'SHOULD NOT BE READ']:
            read.append(part)
            yield part
    with pytest.raises(ValueError, match='download limit'):
        t.bounded_response_body(SimpleNamespace(iter_content=chunks))
    assert len(read)==2
    with pytest.raises(ValueError, match='download limit'):
        t.bounded_response_body(SimpleNamespace(iter_content=lambda **kw:iter([b'%PDF-'+b'x'*30])))


def test_fetch_closes_response_on_size_failure(monkeypatch):
    import gaia_agent.tools as t
    monkeypatch.setattr(t,'HTML_DOWNLOAD_LIMIT',10)
    monkeypatch.setattr(t,'_validate_public_url',lambda u:u)
    closed=[]
    response=SimpleNamespace(is_redirect=False,raise_for_status=lambda:None,
        close=lambda:closed.append(True),iter_content=lambda **kw:iter([b'x'*11]))
    monkeypatch.setattr(t.requests,'get',lambda *a,**kw:response)
    with pytest.raises(ValueError, match='download limit'):
        t.fetch_url('https://example.org')
    assert closed==[True]
