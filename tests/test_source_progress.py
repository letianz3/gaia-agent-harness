import json
from types import SimpleNamespace

from gaia_agent.evidence import evidence_packet
from gaia_agent.source_progress import (
    SourceProgressRegistry,
    explicit_authors,
    source_key,
)
from gaia_agent.tracing import Trace


def test_author_scope_is_conservative():
    assert explicit_authors('Manual written by Alice Example & Bob Sample under an open license?') == ['Alice Example', 'Bob Sample']
    assert explicit_authors('Who won the award?') == []
    assert explicit_authors('Book written by an unknown author?') == []


def test_changed_navigation_cannot_bypass_source_limit_but_other_sources_can():
    calls = []
    def execute(name, args):
        calls.append(args)
        return 'SOURCE: https://example.org/book\nUnrelated manual contents', True
    trace = Trace('test', 'Manual written by Alice Example under an open license?')
    proxy = SourceProgressRegistry(SimpleNamespace(execute=execute), trace)
    for query in ('topic', 'alternate'):
        result, ok = proxy.execute('fetch_url', json.dumps({'url': 'https://example.org/book', 'link_query': query}))
        assert ok and 'not confirmed' in result
    result, ok = proxy.execute('fetch_url', json.dumps({'url': 'https://example.org/book#section', 'link_query': 'third'}))
    assert not ok and 'DIFFERENT' in result and len(calls) == 2
    assert proxy.execute('fetch_url', '{"url":"https://example.org/other"}')[1]
    assert source_key('https://example.org/book?a=1') != source_key('https://example.org/book?a=2')


def test_failed_read_retry_and_evidence_separation():
    trace = Trace('test', 'Manual authored by Alice Example under license?')
    responses = iter([('timeout', False), ('SOURCE: https://example.org/a\ntext', True)])
    proxy = SourceProgressRegistry(SimpleNamespace(execute=lambda *args: next(responses)), trace)
    assert not proxy.execute('fetch_url', '{"url":"https://example.org/a"}')[1]
    raw, ok = proxy.execute('fetch_url', '{"url":"https://example.org/a"}')
    assert ok
    packet = evidence_packet([{'type': 'tool_call', 'name': 'fetch_url', 'succeeded': True, 'result': raw}])
    assert 'Alice Example' not in packet and 'HARNESS SOURCE CHECK' not in packet


def test_successful_prior_reads_seed_recovery_limit():
    trace = Trace('test', 'Question')
    for _ in range(2):
        trace.add('tool_call', name='fetch_url', arguments='{"url":"https://example.org/a"}', succeeded=True, result='SOURCE: https://example.org/a\ntext')
    proxy = SourceProgressRegistry(SimpleNamespace(execute=lambda *args: (_ for _ in ()).throw(AssertionError('no fetch'))), trace)
    assert not proxy.execute('fetch_url', '{"url":"https://example.org/a"}')[1]
