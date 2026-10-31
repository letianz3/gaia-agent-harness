import pytest

from gaia_agent.source_lists import preserve_valid_fields, render_list
from gaia_agent.resolution import census_count, census_identity


def test_schema_repair_preserves_classifications_and_fills_missing_property():
    spec = dict(mode='classify', items=['sample leaf', 'sample dairy'],
                question='Exclude fruits', policy_id='botanical_nonfruit_parts')
    old = {'items': [
        dict(text='sample leaf', include=True, basis='leaf', plant_part='leaf', excluded_by=[]),
        dict(text='sample dairy', include=False, basis='animal product', excluded_by=[])]}
    repair = {'items': [
        dict(text='sample leaf', include=False, basis='culinary label', plant_part='processed', excluded_by=[]),
        dict(text='sample dairy', include=False, basis='animal product', plant_part='nonplant', excluded_by=[])]}
    merged = preserve_valid_fields(old, repair, spec)
    assert render_list(merged, spec) == 'sample leaf'
    assert merged['items'][0] == old['items'][0]
    assert merged['items'][1]['plant_part'] == 'nonplant'
    assert 'plant_part' not in old['items'][1]


def test_reordered_exclusions_cannot_reinterpret_new_flags():
    spec = dict(mode='classify', items=['object'], question='large fragile')
    old = dict(exclusion_criteria=['large', 'fragile'], items=[
        dict(text='object', include=True, basis='measured', excluded_by='invalid')])
    repair = dict(exclusion_criteria=['fragile', 'large'], items=[
        dict(text='object', include=True, basis='measured', excluded_by=[False, True])])
    with pytest.raises(ValueError, match='exclusion'):
        render_list(preserve_valid_fields(old, repair, spec), spec)


def test_missing_fields_remain_invalid_and_unknown_items_cannot_enter():
    spec = dict(mode='classify', items=['x', 'y'])
    old = {'items': [dict(text='x', include=True, basis='observed')]}
    merged = preserve_valid_fields(old, {'items': [dict(text='z', include=True, basis='invented')]}, spec)
    assert [r['text'] for r in merged['items']] == ['x', 'y']
    with pytest.raises(ValueError):
        render_list(merged, spec)


def test_census_collapses_stage_annotations_not_distinct_species():
    def group(key):
        return dict(species_key=key, visual_features='observed', location='left', uncertain=False)
    groups = [group('Example_duck_adult'), group('Example_duck_chick'),
              group('Example duck (juvenile)'), group('Other_duck')]
    assert census_count({'frames': [dict(timestamp=1, groups=groups)]}, [1]) == 2
    assert census_identity(group('Little Penguin')) != census_identity(group('Penguin'))
    assert census_identity(group('Chicken')) == 'chicken'
    with pytest.raises(ValueError):
        census_identity(group('adult'))


def test_life_stage_never_overrides_uncertain_visual_identity():
    group = dict(species_key='Example_duck_chick', visual_features='unclear', location='left', uncertain=True)
    with pytest.raises(ValueError):
        census_count({'frames': [dict(timestamp=1, groups=[group])]}, [1])


def test_explicit_exclusion_short_circuits_irrelevant_properties():
    spec = dict(mode='classify', items=['sample leaf', 'excluded object'],
                question='Exclude synthetic objects', policy_id='botanical_nonfruit_parts')
    report = dict(exclusion_criteria=['synthetic objects'], items=[
        dict(text='sample leaf', include=True, basis='leaf', plant_part='leaf', excluded_by=[False]),
        dict(text='excluded object', include=False, basis='synthetic', excluded_by=[True])])
    assert render_list(report, spec) == 'sample leaf'
    report['items'][1]['excluded_by'] = [False]
    with pytest.raises(ValueError, match='plant_part'):
        render_list(report, spec)


@pytest.mark.parametrize('second,verdict,strict,expected', [
    ('There were 42 research reports.', 'PASS', True, '42'),
    ('There were 43 research reports.', 'PASS', True, 'Unable to verify answer'),
    ('There were 43 research reports.', 'PASS', False, '42'),  # unresolved: incumbent wins the tie
    ('There were 42 research reports.', 'UNCERTAIN', True, '42'),
])
def test_supported_count_equivalence_not_arbitrary_conflict_resolution(second, verdict, strict, expected):
    import json
    from types import SimpleNamespace
    from gaia_agent.verification import compare_answers
    from gaia_agent.tracing import Trace
    evidence = json.dumps(dict(id='E0', kind='observation', excerpt='The archive records 42 research reports.'))
    report = dict(candidates=[dict(id='A', verdict='PASS', evidence_ids=['E0']),
                              dict(id='B', verdict=verdict, evidence_ids=['E0'])])
    for row in report['candidates']:
        row['checks'] = dict(task_constraints=row['verdict'], source_identity='PASS', answer_value='PASS')
    agent = SimpleNamespace(settings=SimpleNamespace(abstain_on_unverified=strict),
                            _plain_completion=lambda *a, **k: SimpleNamespace(
        usage=None, choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(report)))]))
    question = 'How many research reports were published?'
    assert compare_answers(agent, question, '42', second, evidence, Trace('test', question)) == expected


def test_review_aggregate_cannot_override_failed_or_missing_constraint():
    from gaia_agent.verification import aggregate_checks
    row = dict(verdict='PASS', checks=dict(task_constraints='FAIL', source_identity='PASS', answer_value='PASS'))
    assert aggregate_checks(row)['verdict'] == 'FAIL'
    assert row['verdict'] == 'PASS'
    del row['checks']['task_constraints']
    assert aggregate_checks(row)['verdict'] == 'UNCERTAIN'


def test_long_document_keeps_tail_and_middle_query_with_bounded_output():
    from gaia_agent.tools import bounded_document_text
    text = 'Document title\n' + 'padding ' * 6000 + '\nAcknowledgments: award ZZ-987 supports Researcher Q.\n' + 'more ' * 5000 + '\nClosing appendix.'
    excerpt = bounded_document_text(text, 'Acknowledgments')
    assert len(excerpt) <= 30000
    assert 'award ZZ-987 supports Researcher Q.' in excerpt
    assert excerpt.startswith('Document title') and excerpt.endswith('Closing appendix.')
    assert bounded_document_text('short document') == 'short document'


def test_numbered_source_materialization_requires_observed_adjacent_identity():
    from gaia_agent.resolution import ground_numbered_rows
    source = 'https://example.org/2018/register'
    body = '2018 Example historical register\nPitchers\n7\n山田 太郎\n8\n佐藤 次郎\n'
    events = [dict(name='fetch_url', succeeded=True, result='SOURCE: ' + source + '\n' + body)]
    report = dict(source_url=source, time_quote='reworded title', rows=[
        dict(number=7, native_name='山田太郎', quote='7 Pitcher 山田太郎'),
        dict(number=9, native_name='佐藤次郎', quote='9 Pitcher 佐藤次郎')])
    fixed = ground_numbered_rows(report, events, 2018)
    assert fixed['time_quote'] == body.splitlines()[0]
    assert fixed['rows'][0]['quote'] == '7\n山田 太郎'
    assert fixed['rows'][0]['native_name'] == '山田 太郎'
    assert fixed['rows'][1] == report['rows'][1]  # no invented number/name join
    assert ground_numbered_rows(report, [], 2018) == report
    assert report['time_quote'] == 'reworded title'


def test_classification_repair_keeps_valid_rows_and_does_not_run_blanket_audit():
    import json
    from types import SimpleNamespace
    from gaia_agent.source_lists import solve_source_list
    from gaia_agent.tracing import Trace

    question = 'Categorize these items:\n\nred pen, blue cup, red hat, blue box, red ball\n\nAlphabetize a comma separated list.'
    rows = [dict(text=x, include=x.startswith('red'), basis='visible color', excluded_by=[])
            for x in ['red pen', 'blue cup', 'red hat', 'blue box', 'red ball']]
    first = {'items': [dict(r) for r in rows]}
    del first['items'][1]['basis']
    second = {'items': [dict(r, include=False) for r in rows]}
    reports = iter([first, second])
    calls = []
    def complete(*args, **kwargs):
        calls.append(1)
        return SimpleNamespace(usage=None, choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(next(reports))))])
    agent = SimpleNamespace(_plain_completion=complete)
    trace = Trace('synthetic', question)
    assert solve_source_list(agent, question, question, trace) == 'red ball, red hat, red pen'
    assert len(calls) == 2
    assert any(e['type'] == 'source_list_schema_repair' for e in trace.events)

    reports = iter([{'items': rows}])
    calls.clear()
    assert solve_source_list(agent, question, question, Trace('valid', question)) == 'red ball, red hat, red pen'
    assert len(calls) == 1
