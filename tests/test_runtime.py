from types import SimpleNamespace
from dataclasses import replace
import json
import pytest
import threading

from gaia_agent.config import Settings
from gaia_agent.registry import ToolRegistry
from gaia_agent.runtime import ModelGateway, BudgetExceeded
from gaia_agent.orchestration import validate_plan, run_plan
from gaia_agent.agent import BaselineAgent
from gaia_agent.tracing import Trace
from gaia_agent.recovery import FailureTracker


def settings(tmp_path, **kwargs):
    return Settings('https://example.test', '', 'fake', None, 4, 1, 3, 5, tmp_path, **kwargs)


def response(content, calls=None):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=calls or []))],
                           usage=SimpleNamespace(prompt_tokens=10, completion_tokens=2))


def test_guardrails_validate_before_approval_and_deny_by_default():
    registry = ToolRegistry()
    actions, audits = [], []
    registry.audit = lambda **e: audits.append(e)
    registry.register('write', '', {'type':'object', 'properties':{'n':{'type':'integer'}}, 'required':['n']},
                      lambda n: actions.append(n), dangerous=True)
    assert registry.execute('write', '{"n":true}')[1] is False
    assert registry.execute('write', '{"n":1}')[0].startswith('DENIED')
    registry.approval = lambda name, args: True
    assert registry.execute('write', '{"n":2}')[1]
    assert actions == [2]
    assert len([e for e in audits if e['action']=='approval']) == 2


def test_dag_rejects_cycle_and_unknown_agent():
    for plan in [
        [dict(id='A', agent='analyst', task='x', depends_on=['B'])],
        [dict(id='A', agent='evil', task='x', depends_on=[])],
        [dict(id='A', agent='analyst', task='x', depends_on=['A'])],
    ]:
        with pytest.raises(ValueError):
            validate_plan(json.dumps(plan), 4)


def test_gateway_cache_has_no_duplicate_usage_and_budget_is_bounded(tmp_path):
    gateway = ModelGateway(settings(tmp_path, llm_cache_enabled=True, max_llm_calls=1))
    create = lambda **kw: response('answer')
    first = gateway.call(create, model='fake', messages=[])
    cached = gateway.call(create, model='fake', messages=[])
    assert first.usage.prompt_tokens == 10
    assert cached.usage is None
    assert gateway.calls == 1 and gateway.hits == 1
    with pytest.raises(BudgetExceeded):
        gateway.call(create, model='different', messages=[])


def test_dag_passes_evidence_and_restricts_specialist_tools(tmp_path):
    plan = [dict(id='A', agent='researcher', task='Find actor', depends_on=[]),
            dict(id='B', agent='analyst', task='Calculate', depends_on=['A'])]
    plain = iter([response(json.dumps(plan)), response('42')])
    agent = BaselineAgent(settings(tmp_path), client=object())
    agent._plain_completion = lambda messages: next(plain)
    received = []
    def loop(messages, registry, *args, **kwargs):
        received.append((messages, registry.names()))
        return 'actor evidence' if len(received)==1 else '42'
    agent._run_tool_loop = loop
    registry = ToolRegistry()
    for name in ['search_web', 'run_python']:
        registry.register(name, '', {'type':'object'}, lambda: '')
    trace = Trace('id', 'q')
    assert run_plan(agent, 'q', 'q', registry, trace) == '42'
    assert received[0][1] == ['search_web']
    assert received[1][1] == ['run_python']
    assert 'actor evidence' in received[1][0][1]['content']


def test_duplicate_failure_calls_in_same_batch_are_blocked(tmp_path):
    calls = [SimpleNamespace(id=str(i), function=SimpleNamespace(name='bad', arguments='{}')) for i in range(3)]
    replies = iter([response(None, calls), response('done')])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw:next(replies))))
    agent = BaselineAgent(settings(tmp_path, parallel_tools_enabled=True, memory_enabled=False), client)
    registry = ToolRegistry()
    count = []
    def bad():
        count.append(1)
        raise ValueError('fail')
    registry.register('bad', '', {'type':'object'}, bad, parallel_safe=True)
    trace = Trace('id', 'q')
    agent._run_tool_loop([{'role':'user','content':'q'}], registry, trace, 3, 'agent', failure_tracker=FailureTracker(2))
    assert len(count) == 2
    assert sum(e.get('blocked', False) for e in trace.events) == 1


def test_independent_specialists_overlap(tmp_path):
    plan = [dict(id=x, agent='researcher', task=x, depends_on=[]) for x in ['A', 'B']]
    replies = iter([response(json.dumps(plan)), response('done')])
    agent = BaselineAgent(settings(tmp_path, parallel_tools_enabled=True), client=object())
    agent._plain_completion = lambda messages: next(replies)
    barrier = threading.Barrier(2)
    def loop(*args, **kwargs):
        barrier.wait(timeout=2)
        return 'evidence'
    agent._run_tool_loop = loop
    trace = Trace('id', 'q')
    run_plan(agent, 'q', 'q', ToolRegistry(), trace)
    assert all(e['status']=='COMPLETED' for e in trace.events if e['type']=='subtask_result')


def test_dependency_failure_prevents_downstream_execution(tmp_path):
    plan = [dict(id='A', agent='researcher', task='A', depends_on=[]),
            dict(id='B', agent='analyst', task='B', depends_on=['A'])]
    replies = iter([response(json.dumps(plan)), response('unknown')])
    agent = BaselineAgent(settings(tmp_path), client=object())
    agent._plain_completion = lambda messages: next(replies)
    calls = []
    def loop(*args, **kwargs):
        calls.append(1)
        raise RuntimeError('unavailable')
    agent._run_tool_loop = loop
    trace = Trace('id', 'q')
    run_plan(agent, 'q', 'q', ToolRegistry(), trace)
    assert len(calls)==1
    assert all(e['status']=='FAILED' for e in trace.events if e['type']=='subtask_result')
