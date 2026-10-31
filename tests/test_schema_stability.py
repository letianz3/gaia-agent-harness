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
