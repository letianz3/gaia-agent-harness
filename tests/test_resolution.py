import pytest
from gaia_agent.resolution import item_evidence,census_count,temporal_neighbors

def page(body):
 return dict(type='tool_call',name='fetch_url',succeeded=True,result='SOURCE: https://example.org/archive\n'+body)

def test_item_evidence_recovers_middle_not_only_head_tail():
 body='Header '+('x'*4000)+'\nBlue widget is excluded because it contains alloy.\n'+('y'*4000)
 assert 'contains alloy' in item_evidence([page(body)],['Blue widget'])

def test_counts_distinct_species_within_frame_not_across_frames():
 def group(key):return dict(species_key=key,visual_features='visible trait',location='left',uncertain=False)
 report={'frames':[{'timestamp':1,'groups':[group('A'),group('A'),group('B')]},{'timestamp':2,'groups':[group('C')]}]}
 assert census_count(report,[1,2])==2
 report['frames'][0]['groups'][0]['uncertain']=True
 with pytest.raises(ValueError):census_count(report,[1,2])

def test_census_rejects_missing_or_invented_frame():
 with pytest.raises(ValueError):census_count({'frames':[{'timestamp':9,'groups':[]}]},[1])
 with pytest.raises(ValueError):census_count({'frames':[{'timestamp':1,'groups':[]}]},[1,2])

def roster():
 return dict(year=2018,source_url='https://example.org/archive',time_quote='Official 2018 season roster',target_number=8,rows=[
  dict(number=n,surname=s,eligible=True,quote=f'Number {n} Player {s}') for n,s in [(9,'Delta'),(7,'Alpha'),(8,'Target')]])

def test_temporal_neighbors_sort_numbers_and_require_dated_evidence():
 r=roster(); body=r['time_quote']+'\n'+'\n'.join(x['quote'] for x in r['rows'])
 assert temporal_neighbors(r,2018,[page(body)])=='Alpha, Delta'
 with pytest.raises(ValueError):temporal_neighbors(r,2018,[page('UPDATE:At the end of 2024 season\n'+body)])
 r['rows'][0]['number']=10
 with pytest.raises(ValueError):temporal_neighbors(r,2018,[page(body)])

def test_temporal_rejects_fabricated_period_quote():
 r=roster()
 with pytest.raises(ValueError):temporal_neighbors(r,2018,[page('Current roster with no historical provenance')])

def test_temporal_sampling_fills_late_gaps():
 from gaia_agent.media_tools import coverage_times
 times=coverage_times([30,35,40],120)
 assert len(times)==6 and max(times)>90 and {30,35,40}.issubset(times)
 assert all(0<=t<120 for t in times)

def test_plant_part_rules_override_culinary_membership():
 from gaia_agent.source_lists import render_list
 report={'items':[dict(text='unknown seed',include=True,basis='edible seed',plant_part='seed',excluded_by=[]),dict(text='unknown leaf',include=True,basis='edible leaf',plant_part='leaf',excluded_by=[])]}
 assert render_list(report,dict(mode='classify',items=['unknown seed','unknown leaf'],plant_parts=True))=='unknown leaf'
