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


def test_distinct_sources_remain_concurrent():
    import threading
    from concurrent.futures import ThreadPoolExecutor

    barrier = threading.Barrier(2)
    def execute(name, args):
        barrier.wait(timeout=2)
        return 'SOURCE: ' + json.loads(args)['url'] + '\ntext', True
    proxy = SourceProgressRegistry(SimpleNamespace(execute=execute), Trace('test', 'Question'))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda path: proxy.execute('fetch_url', json.dumps({'url': 'https://example.org/' + path})), ['a', 'b']))
    assert all(ok for _, ok in results)


def test_navigation_json_remains_parseable_and_same_source_budget_is_atomic():
    from concurrent.futures import ThreadPoolExecutor

    marker = '\nNAVIGATION LINKS (discovery only, not factual evidence):\n'
    def execute(name, args):
        return 'SOURCE: https://example.org/a\ntext' + marker + '[{"url":"https://example.org/b"}]', True
    proxy = SourceProgressRegistry(SimpleNamespace(execute=execute), Trace('test', 'Manual written by Alice Example under license?'))
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda i: proxy.execute('fetch_url', json.dumps({'url': 'https://example.org/a', 'link_query': str(i)})), range(4)))
    assert sum(ok for _, ok in results) == 2
    for raw, ok in results:
        if ok:
            assert json.loads(raw.split(marker)[1])[0]['url'] == 'https://example.org/b'


def test_blocked_reread_returns_stored_literal_tables_not_a_bare_refusal():
    body = 'SOURCE: https://example.org/counts\nCounts page\n[TABLE 1: 2 rows x 2 columns]\n| Code | Total |\n| AAA | 3 |\n| BBB | 1 |\n[END TABLE 1]\nFooter'
    trace = Trace('test', 'Which code has the least total? If tied, alphabetical.')
    for _ in range(2):
        trace.add('tool_call', name='fetch_url', arguments='{"url":"https://example.org/counts"}', succeeded=True, result=body)
    proxy = SourceProgressRegistry(SimpleNamespace(execute=lambda *a: (_ for _ in ()).throw(AssertionError('no fetch'))), trace)
    raw, ok = proxy.execute('fetch_url', '{"url":"https://example.org/counts"}')
    assert not ok  # not a new observation
    assert 'CACHED SOURCE TEXT' in raw and '| BBB | 1 |' in raw and 'Counts page' in raw
