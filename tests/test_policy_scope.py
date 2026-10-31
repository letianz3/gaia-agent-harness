import pytest
from types import SimpleNamespace
from gaia_agent.policies import select_list_policy,wants_species_census,historical_neighbor_year,PropertyPolicy,POLICIES
from gaia_agent.tracing import Trace

@pytest.mark.parametrize('question',[
 'A botanist is cooking. Classify vegetables in the everyday culinary sense.',
 'List culinary vegetables, excluding botanical fruits.',
 'Classify botanical fruits and vegetables into both categories.',
 'Which vegetables contain vitamin C?',
 'List words alphabetically: leaf, seed, root, fruit, flower.',
 'Classify industrial materials, excluding metals.',
])
def test_domain_policy_abstains_outside_explicit_scope(question):
 assert select_list_policy(question) is None

def test_policy_needs_explicit_exclusion_and_can_be_disabled():
 q='Classify vegetables; exclude botanical fruits.'
 assert select_list_policy(q)=='botanical_nonfruit_parts'
 assert select_list_policy(q,enabled=False) is None

@pytest.mark.parametrize('question',[
 'As of 2018, which version numbers come before and after version 4?',
 'As of 2018, list surnames nearest the available numbers before and after 9.',
 'As of 2018, which surnames are alphabetically before and after Ali?',
])
def test_temporal_strategy_does_not_hijack_other_orderings(question):
 assert historical_neighbor_year(question) is None

def test_video_census_does_not_hijack_identification_or_non_simultaneous_counts():
 assert not wants_species_census('Describe species interacting at the same time.')
 assert not wants_species_census('How many species appear throughout the video?')
 assert wants_species_census('What is the maximum number of species visible simultaneously?')

def test_recent_retrospective_is_not_rejected_as_current_roster():
 from gaia_agent.resolution import temporal_source_conflict
 assert not temporal_source_conflict('UPDATE: 2025\n2017 season roster\nHistoric rows',2017)
 assert temporal_source_conflict('UPDATE: 2025\nCurrent roster\nCopyright 2017-2025',2017)
 assert temporal_source_conflict('UPDATE: 2025\nCurrent roster\nNAVIGATION LINKS\n2017 roster',2017)

def test_property_executor_supports_unrelated_domain(monkeypatch):
 from gaia_agent.source_lists import render_list
 policy=PropertyPolicy('materials','conductivity',frozenset(('conductive','insulating')),frozenset(('conductive',)),(), 'test')
 monkeypatch.setitem(POLICIES,policy.name,policy)
 spec=dict(mode='classify',items=['sample A','sample B'],policy_id='materials')
 rows=[dict(text='sample A',include=False,basis='measured',conductivity='conductive',excluded_by=[]),dict(text='sample B',include=True,basis='measured',conductivity='insulating',excluded_by=[])]
 assert render_list({'items':rows},spec)=='sample A'

def test_disable_strategy_dispatch_avoids_specialized_calls():
 from gaia_agent.workflows import solve_specialized
 trace=Trace('test','test')
 agent=SimpleNamespace(settings=SimpleNamespace(specialized_workflows_enabled=False))
 assert solve_specialized(agent,'question',[],None,None,trace) is None
 assert trace.events[-1]['strategy']=='general'
