from types import SimpleNamespace

from gaia_agent.agent import BaselineAgent
from gaia_agent.registry import ToolRegistry
from gaia_agent.tracing import Trace


def test_early_final_json_exit_repairs_multiple_objects_once():
    agent = BaselineAgent.__new__(BaselineAgent)
    agent.settings = SimpleNamespace(parallel_tools_enabled=False)
    agent._compress_history = lambda messages, *args: messages
    def response(content):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=[]))], usage=None)
    agent._completion = lambda *args: response('{"rows":[]}\n{"answer":"extra"}')
    calls = []
    def repair(messages, **kwargs):
        calls.append(kwargs)
        return response('{"rows":[]}')
    agent._plain_completion = repair
    trace = Trace('test', 'Return JSON')
    assert agent._run_tool_loop([], ToolRegistry(), trace, 1, 'subtask', final_json=True) == '{"rows":[]}'
    assert calls == [{'response_format': {'type': 'json_object'}}]
    assert any(e['type'] == 'structured_output_repair' for e in trace.events)
    agent._completion = lambda *args: response('{"rows":[]}')
    agent._run_tool_loop([], ToolRegistry(), trace, 1, 'subtask', final_json=True)
    assert len(calls) == 1
