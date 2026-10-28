from decimal import Decimal
from types import SimpleNamespace
import pytest
from gaia_agent.contracts import aggregate_contract,validate_entity,project_first_name
from gaia_agent.typed_workflows import read_wide_table,validate_chain,solve_entity
from gaia_agent.tracing import Trace


def table_contract():
    return dict(operation='sum',rules=[dict(id='r',question_span='excluding returns',effect='exclude')],
                columns=[dict(column='Sales',matches={'r':False},basis='ordinary sales'),
                         dict(column='Returns',matches={'r':True},basis='returns')])


def test_decimal_aggregation_and_exclusion_are_code_owned():
    total,inc,exc=aggregate_contract(table_contract(),'sum excluding returns',{'Sales':Decimal('0.3'),'Returns':Decimal('0.1')})
    assert total==Decimal('0.3') and inc==['Sales'] and exc==['Returns']


def test_no_invented_exclusion_or_silent_column_omission():
    c=table_contract(); c['rules'][0]['question_span']='excluding taxes'
    with pytest.raises(ValueError,match='explicit question'):
        aggregate_contract(c,'sum excluding returns',{'Sales':Decimal(1),'Returns':Decimal(2)})
    c=table_contract(); c['columns'].pop()
    with pytest.raises(ValueError,match='every numeric column'):
        aggregate_contract(c,'sum excluding returns',{'Sales':Decimal(1),'Returns':Decimal(2)})
    c=table_contract(); c['columns'][0]['matches']['r']=None
    with pytest.raises(ValueError,match='unknown'):
        aggregate_contract(c,'sum excluding returns',{'Sales':Decimal(1),'Returns':Decimal(2)})


def observation(body):
    return dict(type='tool_call',name='fetch_url',succeeded=True,result='SOURCE: https://example.org/cast\n'+body)


def entity_report():
    return dict(status='FOUND',subject_name='Dana Actor',entity=dict(type='character',name='Robin Example',
                first_name='Robin',name_parts_status='unambiguous'),
                support=[dict(source_url='https://example.org/cast',quote='Dana Actor plays Robin Example in the series.')])


def test_entity_join_and_projection():
    r=entity_report();events=[observation(r['support'][0]['quote'])]
    entity=validate_entity(r,'character',dict(name='Dana Actor'),events)
    assert project_first_name(entity)=='Robin'
    r['entity']['type']='person'
    with pytest.raises(ValueError,match='type'):
        validate_entity(r,'character',dict(name='Dana Actor'),events)


def test_empty_page_and_disconnected_entities_are_not_evidence():
    r=entity_report()
    with pytest.raises(ValueError,match='quotation absent'):
        validate_entity(r,'character',dict(name='Dana Actor'),[observation('')])
    with pytest.raises(ValueError,match='predecessor'):
        validate_entity(r,'character',dict(name='Different Actor'),[observation(r['support'][0]['quote'])])


def test_compound_names_are_not_split_and_ambiguity_is_not_guessed():
    assert project_first_name(dict(name='Mary Anne Example',first_name='Mary Anne',name_parts_status='explicit'))=='Mary Anne'
    with pytest.raises(ValueError,match='ambiguous'):
        project_first_name(dict(name='Unknown Name',first_name='Unknown',name_parts_status='ambiguous'))


def test_type_chain_rejects_mismatched_dependencies():
    with pytest.raises(ValueError,match='type chain'):
        validate_chain({'steps':[dict(task='Identify the creator of Example Film',input_type=None,output_type='person'),
                                 dict(task='role',input_type='place',output_type='character')]})


def test_unresolved_prerequisite_blocks_remaining_steps(monkeypatch):
    import gaia_agent.typed_workflows as w
    monkeypatch.setattr(w,'ask_json',lambda *a:{'steps':[
        dict(task='Identify the creator of Example Film',input_type=None,output_type='person'),
        dict(task='role',input_type='person',output_type='character')]})
    calls=[]
    def loop(*args):
        calls.append(args[3]);return '{"status":"NOT_FOUND"}'
    agent=SimpleNamespace(_run_tool_loop=loop)
    from gaia_agent.registry import ToolRegistry
    registry=ToolRegistry()
    trace=Trace('synthetic','first name')
    assert solve_entity(agent,'Give only the first name',registry,trace)=='Unable to verify the requested entity'
    assert calls==[4,2]
    assert any(e['type']=='entity_chain_blocked' and e['step']==0 for e in trace.events)


def test_wide_table_exact_totals_and_total_row_rejection(tmp_path):
    from openpyxl import Workbook
    book=Workbook();sheet=book.active
    sheet.append(['Site','Sales','Returns']);sheet.append(['A',0.1,1]);sheet.append(['B',0.2,2])
    path=tmp_path/'data.xlsx';book.save(path)
    assert read_wide_table(path)=={'Sales':Decimal('0.3'),'Returns':Decimal(3)}
    sheet.append(['Total',0.3,3]);book.save(path)
    with pytest.raises(ValueError,match='double counting'):
        read_wide_table(path)


def test_biography_heading_can_join_its_original_table_row():
    r=entity_report();r['support'][0]['quote']='Example series: Robin Example (supporting role)'
    r['support'][0]['subject_quote']='Dana Actor - Biography'
    body='Dana Actor - Biography\nFilmography\nExample series: Robin Example (supporting role)'
    assert validate_entity(r,'character',dict(name='Dana Actor'),[observation(body)])['name']=='Robin Example'
    r['support'][0]['subject_quote']='Different person biography'
    with pytest.raises(ValueError):
        validate_entity(r,'character',dict(name='Dana Actor'),[observation(body)])


def test_xlsx_missing_dimension_metadata_is_supported(tmp_path):
    from openpyxl import Workbook
    import zipfile,re
    path=tmp_path/'normal.xlsx';book=Workbook();book.active.append(['Site','Revenue']);book.active.append(['A',12]);book.save(path)
    target=tmp_path/'no_dimension.xlsx'
    with zipfile.ZipFile(path) as src,zipfile.ZipFile(target,'w') as out:
        for name in src.namelist():
            data=src.read(name)
            if name=='xl/worksheets/sheet1.xml':data=re.sub(rb'<dimension[^>]*/>',b'',data)
            out.writestr(name,data)
    assert read_wide_table(target)=={'Revenue':Decimal(12)}


def test_placeholder_plan_is_not_a_task():
    with pytest.raises(ValueError,match='placeholder'):
        validate_chain({'steps':[dict(task='lookup including all original constraints',input_type=None,output_type='person')]})


def test_exclusion_cannot_be_reversed_into_inclusion():
    c=table_contract();c['rules'][0]['effect']='include'
    with pytest.raises(ValueError,match='exclusion cannot'):
        aggregate_contract(c,'sum excluding returns',{'Sales':Decimal(1),'Returns':Decimal(2)})


def test_formula_column_does_not_silently_disappear(tmp_path):
    from openpyxl import Workbook
    book=Workbook();book.active.append(['Cash','Credit']);book.active.append([3,'=2+2'])
    path=tmp_path/'formula.xlsx';book.save(path)
    with pytest.raises(ValueError,match='formula cells'):
        read_wide_table(path)


def test_next_step_can_reuse_previously_retrieved_evidence(monkeypatch):
    import json
    import gaia_agent.typed_workflows as w
    from gaia_agent.registry import ToolRegistry
    monkeypatch.setattr(w,'ask_json',lambda *a:{'steps':[
        dict(task='Identify actor from Example Film',input_type=None,output_type='person'),
        dict(task='Find role in Example Series',input_type='person',output_type='character')]})
    trace=Trace('synthetic','first name')
    body='Dana Actor plays Robin Example in the series.'
    replies=iter([
        dict(status='FOUND',entity=dict(type='person',name='Dana Actor'),support=[dict(source_url='https://example.org/cast',quote=body)]),
        entity_report()])
    def loop(*args):
        if not any(e.get('name')=='fetch_url' for e in trace.events):trace.events.append(observation(body))
        return json.dumps(next(replies))
    agent=SimpleNamespace(_run_tool_loop=loop)
    assert solve_entity(agent,'Give only the first name',ToolRegistry(),trace)=='Robin'
