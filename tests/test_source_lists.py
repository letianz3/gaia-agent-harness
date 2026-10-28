import json
from types import SimpleNamespace
import pytest
from gaia_agent.source_lists import list_source, render_list, solve_source_list
from gaia_agent.tracing import Trace


def row(text, include=True):
    return dict(text=text, include=include, basis='criterion from question')


def test_extraction_rejects_paraphrase_and_preserves_original_modifiers():
    spec = dict(mode='extract', source='Use freshly grated ginger and toasted sesame oil.')
    with pytest.raises(ValueError, match='original-source span'):
        render_list({'items':[row('fresh ginger')]}, spec)
    assert render_list({'items':[row('toasted sesame oil'), row('freshly grated ginger')]}, spec) == 'freshly grated ginger, toasted sesame oil'


def test_classification_requires_excluded_items_too():
    spec = dict(mode='classify', items=['red apple','blue cup','red pen'])
    with pytest.raises(ValueError, match='EVERY'):
        render_list({'items':[row('red apple'), row('red pen')]},spec)
    assert render_list({'items':[row('red pen'),row('blue cup',False),row('red apple')]},spec) == 'red apple, red pen'


@pytest.mark.parametrize('items', [[row('x'), row('x')], [dict(text='x',include='false',basis='b')]])
def test_bad_decisions_are_rejected(items):
    with pytest.raises(ValueError):
        render_list({'items':items},dict(mode='extract',source='x'))


def test_routing_ignores_external_and_spreadsheet_questions():
    assert list_source('Find authors online; alphabetize a comma separated list.', 'context') is None
    assert list_source('Calculate food sales from Excel.', 'context') is None
    assert list_source('Classify: red, blue, green.', 'context') is None
    q='Categorize these items:\n\nred pen, blue cup, red hat, blue box, red ball\n\nAlphabetize a comma separated list.'
    assert list_source(q,q)['items'] == ['red pen','blue cup','red hat','blue box','red ball']


def test_extraction_uses_transcript_not_question_examples():
    q='List ingredients, alphabetize as a comma separated list; salt is an example.'
    spec=list_source(q,q+'\n\nTranscript of sample.mp3:\nMix black pepper.')
    assert spec['source']=='Mix black pepper.'
    assert 'salt' not in spec['source']


def test_contract_repair_is_bounded_and_falls_back():
    calls=[]
    def completion(*args,**kwargs):
        calls.append(1)
        return SimpleNamespace(usage=None,choices=[SimpleNamespace(message=SimpleNamespace(content='{}'))])
    agent=SimpleNamespace(_plain_completion=completion)
    q='List ingredients alphabetized, comma separated.'
    assert solve_source_list(agent,q,q+'\nTranscript of a.mp3:\nUse cloves.',Trace('test',q)) is None
    assert len(calls)==2


def test_explicit_exclusion_overrides_category_membership():
    spec=dict(mode='classify', items=['large red box','small red box'])
    report={'exclusion_criteria':['large objects'], 'items':[
        dict(row('large red box'),excluded_by=[True]),
        dict(row('small red box'),excluded_by=[False])]}
    assert render_list(report,spec)=='small red box'
    report['items'][0]['excluded_by']=[]
    with pytest.raises(ValueError,match='every explicit exclusion'):
        render_list(report,spec)
