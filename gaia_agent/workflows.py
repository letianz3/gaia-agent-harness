"""Optional strategy dispatch, isolated from the general agent execution loop."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Strategy:
    name: str
    run: object


def solve_specialized(agent,question,files,context,registry,trace):
    if not agent.settings.specialized_workflows_enabled:
        trace.add('workflow_route',strategy='general',reason='specialized strategies disabled')
        return None
    from .resolution import solve_temporal_neighbors
    from .typed_workflows import solve_typed_task
    from .source_lists import solve_source_list
    strategies=(
        Strategy('historical_numeric_neighbors',lambda:solve_temporal_neighbors(agent,question,registry,trace)),
        Strategy('typed_table_or_entity',lambda:solve_typed_task(agent,question,files,registry,trace)),
        Strategy('source_grounded_list',lambda:solve_source_list(agent,question,context,trace,registry)))
    for strategy in strategies:
        answer=strategy.run()
        if answer is not None:
            trace.add('workflow_route',strategy=strategy.name,reason='applicable strategy returned a result; see contract events for success or blocked status')
            return answer
    trace.add('workflow_route',strategy='general',reason='no supported specialized contract')
    return None
