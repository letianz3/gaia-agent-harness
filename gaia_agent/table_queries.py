"""Declarative queries over observed tables: the model writes, a reviewer checks, code executes.

Many answers are a deterministic operation over one complete collection: the
fewest/most of something with a tie rule, how many rows satisfy constraints,
a total, or the value in the row that satisfies constraints. Models choose the
right table and columns reliably but compare dozens of numbers, count rows and
apply tie rules unreliably. This module therefore splits the work:

1. the model writes a small query spec (table, operation, columns, filters,
   tie rule) or declares the question not applicable - no question regexes;
2. code validates the spec against the parsed table and executes it;
3. when the computed value disagrees with the solver's answer, an independent
   reviewer judges the SPEC's semantics against the question (scope, column
   meaning, every constraint) - a local check models do well - and only a
   reviewed spec may change the answer.

Tables come from the rendered `[TABLE]` blocks of fetched pages; incomplete
blocks are never used. No task IDs, entity names or answer constants appear.
"""
from __future__ import annotations

import json
import re
import unicodedata

from .web_tables import parse_table_blocks

OPERATIONS = ('min', 'max', 'count', 'sum', 'value')
FILTER_OPS = ('eq', 'ne', 'contains', 'not_contains', 'between', 'ge', 'le', 'gt', 'lt')
_AGGREGATE = re.compile(r'^(?:totals?|grand total|all|overall|sum|average|mean|subtotal)\b', re.I)
MAX_TABLES_SHOWN = 8
MAX_ROWS_FOR_QUERY = 2000


def canonical(text):
    return ' '.join(unicodedata.normalize('NFKC', str(text or '')).split())


def parse_value(text):
    """Plain numbers only (thousands separators allowed); units and ranges are not guessed."""
    value = canonical(text).replace(',', '').replace('−', '-')
    value = re.sub(r'\s*\[\s*\w{1,3}\s*\]$', '', value)  # trailing footnote marker such as [a] or [12]
    if re.fullmatch(r'-?\d+(?:\.\d+)?', value):
        return float(value)
    return None


def observed_tables(events):
    tables, seen = [], set()
    for index, event in enumerate(events):
        raw = event.get('result', '')
        if (event.get('type') != 'tool_call' or event.get('name') != 'fetch_url'
                or not event.get('succeeded') or not raw.startswith('SOURCE: ')):
            continue
        source, body = raw.split('\n', 1)
        body = body.split('\nNAVIGATION LINKS', 1)[0]
        for block in parse_table_blocks(body):
            key = (source, json.dumps(block['rows'], ensure_ascii=False))
            if (not block['complete'] or len(block['rows']) < 2 or key in seen
                    or len(block['rows']) > MAX_ROWS_FOR_QUERY):
                continue
            seen.add(key)
            title = body.split('\n', 1)[0][:200]
            tables.append(dict(block, id=f'T{len(tables) + 1}', event=index, source=source[8:], title=title))
    return tables


def table_summary(table, sample=3):
    return {'table_id': table['id'], 'source': table['source'], 'page_title': table['title'],
            'row_count': len(table['rows']),
            'columns': {str(i): name for i, name in enumerate(table['columns'])},
            'sample_rows': table['rows'][:sample]}


def _column(spec, key, width, required=True):
    value = spec.get(key)
    if value is None and not required:
        return None
    if type(value) is not int or not 0 <= value < width:
        raise ValueError(f'{key} must be a column index between 0 and {width - 1}')
    return value


def _matches(cell, condition):
    op, target = condition['op'], condition.get('value')
    text = canonical(cell).casefold()
    if op in ('eq', 'ne', 'contains', 'not_contains'):
        wanted = canonical(target).casefold()
        if op == 'eq':
            return text == wanted
        if op == 'ne':
            return text != wanted
        return (wanted in text) == (op == 'contains')
    number = parse_value(cell)
    if number is None:
        # A leading year/number with an annotation ("2005 (reissue)") is common in records.
        lead = re.match(r'\s*(-?\d+(?:\.\d+)?)\b', canonical(cell))
        number = float(lead[1]) if lead else None
    if number is None:
        return False
    low = parse_value(str(target))
    if low is None:
        raise ValueError(f'filter value {target!r} is not numeric for {op}')
    if op == 'between':
        high = parse_value(str(condition.get('value2')))
        if high is None:
            raise ValueError('between requires numeric value and value2')
        return low <= number <= high
    return {'ge': number >= low, 'le': number <= low, 'gt': number > low, 'lt': number < low}[op]


def _render_number(value):
    return str(int(value)) if float(value).is_integer() else repr(round(value, 10)).rstrip('0').rstrip('.')


def execute_query(table, spec):
    """Validate and execute one spec. Raises ValueError instead of guessing."""
    width = len(table['columns'])
    operation = spec.get('operation')
    if operation not in OPERATIONS:
        raise ValueError('operation must be one of ' + ', '.join(OPERATIONS))
    entity_column = _column(spec, 'entity_column', width)
    value_column = _column(spec, 'value_column', width, required=operation in ('min', 'max', 'sum'))
    answer_column = _column(spec, 'answer_column', width, required=operation in ('min', 'max', 'value'))
    filters = spec.get('filters') or []
    if not isinstance(filters, list):
        raise ValueError('filters must be a list')
    for condition in filters:
        if not isinstance(condition, dict) or condition.get('op') not in FILTER_OPS:
            raise ValueError('each filter needs op in ' + ', '.join(FILTER_OPS))
        _column(condition, 'column', width)
        if not isinstance(condition.get('question_span'), str) or not condition['question_span'].strip():
            raise ValueError('each filter must quote the question phrase it implements (question_span)')
    rows, aggregates = [], 0
    for row in table['rows']:
        entity = canonical(row[entity_column])
        if not entity or _AGGREGATE.match(entity):
            aggregates += 1
            continue
        if all(_matches(row[c['column']], c) for c in filters):
            rows.append(row)
    result = {'operation': operation, 'matched_rows': len(rows), 'excluded_aggregate_rows': aggregates}
    if operation == 'count':
        result['answer'] = str(len(rows))
        result['rows'] = rows[:60]
        return result
    if not rows:
        raise ValueError('no rows satisfy the filters')
    if operation == 'value':
        if len(rows) != 1:
            raise ValueError(f'value lookup must match exactly one row, matched {len(rows)}')
        result.update(answer=canonical(rows[0][answer_column]), row=rows[0])
        return result
    measured = [(parse_value(row[value_column]), row) for row in rows]
    numeric = [(v, row) for v, row in measured if v is not None]
    if len(numeric) < max(1, 0.8 * len(measured)):
        raise ValueError('value column is not numeric for most matching rows; wrong column or incomplete data')
    if operation == 'sum':
        result['answer'] = _render_number(sum(v for v, _ in numeric))
        return result
    if len(numeric) < 2:
        raise ValueError('an extremum needs at least two measurable rows')
    best = (min if operation == 'min' else max)(v for v, _ in numeric)
    tied = [row for v, row in numeric if v == best]
    tie_rule = spec.get('tie_break', 'none')
    if len(tied) > 1:
        if tie_rule == 'alphabetical':
            key = _column(spec, 'tie_break_column', width)
            tied.sort(key=lambda row: canonical(row[key]).casefold())
        elif tie_rule != 'first_in_table':
            raise ValueError('tie between ' + ', '.join(canonical(r[answer_column]) for r in tied) +
                             ' and the question gives no tie rule')
    answer = canonical(tied[0][answer_column])
    if not answer:
        raise ValueError('selected row has an empty answer cell')
    result.update(answer=answer, value=_render_number(best), row=tied[0],
                  tied=[canonical(r[answer_column]) for r in tied], measured_rows=len(numeric))
    return result


SPEC_PROMPT = (
    'Decide whether the answer to the question is a deterministic operation over ONE of the observed '
    'tables below, where that table is the complete collection the question ranges over. If not, '
    'or if no table measures exactly the requested scope (date, edition, entity type), return '
    '{"applicable":false,"reason":"..."}. Do not compute the answer yourself.\n'
    'Otherwise return {"applicable":true,"table_id":"T1","operation":"min|max|count|sum|value",'
    '"entity_column":0,"value_column":3,"answer_column":0,'
    '"filters":[{"column":2,"op":"eq|ne|contains|not_contains|between|ge|le|gt|lt","value":"...",'
    '"value2":"upper bound for between","question_span":"exact question phrase this filter implements"}],'
    '"tie_break":"alphabetical|first_in_table|none","tie_break_column":0,'
    '"basis":"why this table, columns and filters implement EVERY constraint in the question"}.\n'
    'Use column indices. entity_column identifies each row (rows with blank or total labels are ignored). '
    'value_column holds the measured number (min/max/sum). answer_column holds what the question asks '
    'you to output. count returns the number of matching rows. value returns the answer cell of the '
    'single row matching the filters. Encode every inclusion/exclusion/date bound as a filter; '
    'prefer an overall total column over a subgroup column when the question asks for the overall quantity. '
    'Use tie_break only if the question states a tie rule.')

REVIEW_PROMPT = (
    'Review a proposed table query BEFORE it is executed by code. Judge only whether the query '
    'faithfully implements the question: correct table scope (date/edition/entity type), the value '
    'column measures exactly the requested quantity, every constraint in the question is encoded as a '
    'filter with the right bounds (inclusive/exclusive), no filter adds a constraint the question lacks, '
    'the answer column gives the requested output form, and the tie rule matches the question. '
    'Do not compute or guess the answer. Return JSON {"verdict":"PASS|FAIL","problems":["..."]}.')


def propose_query(agent, question, tables, trace, label):
    from .contracts import ask_json
    shown = tables[:MAX_TABLES_SHOWN]
    spec = ask_json(agent, SPEC_PROMPT + '\nQuestion: ' + question + '\nObserved tables: ' +
                    json.dumps([table_summary(t) for t in shown], ensure_ascii=False), trace)
    trace.add('table_query_spec', label=label, spec=spec)
    return spec


def review_query(agent, question, table, spec, trace):
    from .contracts import ask_json
    review = ask_json(agent, REVIEW_PROMPT + '\nQuestion: ' + question + '\nTable: ' +
                      json.dumps(table_summary(table, sample=5), ensure_ascii=False) +
                      '\nProposed query: ' + json.dumps(spec, ensure_ascii=False), trace)
    passed = review.get('verdict') == 'PASS'
    trace.add('table_query_review', verdict='PASS' if passed else 'FAIL', problems=review.get('problems', []))
    return passed


def computed_answer(agent, question, trace):
    """Return {'answer', 'result', 'spec'} for an applicable, executable query, else None."""
    tables = observed_tables(trace.events)
    if not tables:
        return None
    spec = propose_query(agent, question, tables, trace, 'primary')
    if spec.get('applicable') is not True:
        return None
    table = next((t for t in tables if t['id'] == spec.get('table_id')), None)
    if table is None:
        trace.add('table_query_rejected', reason='unknown table_id', spec=spec)
        return None
    try:
        result = execute_query(table, spec)
    except (ValueError, TypeError, KeyError) as exc:
        trace.add('table_query_rejected', reason=str(exc), spec=spec)
        return None
    trace.add('table_query_executed', source=table['source'], table=table['id'],
              **{k: v for k, v in result.items() if k != 'rows'},
              scope='complete observed table; spec semantics are a model choice until reviewed')
    return {'answer': result['answer'], 'result': result, 'spec': spec, 'table': table}


def agrees(candidate, computed):
    """The candidate names the selected value, or another identity cell of the selected row."""
    value = canonical(candidate).casefold()
    if not value:
        return False
    if value == canonical(computed['answer']).casefold():
        return True
    row = computed['result'].get('row')
    if row is not None and parse_value(candidate) is None:
        # Another identity of the same row (a name for a code); never a numeric cell,
        # which could coincide with an unrelated measurement.
        return any(canonical(cell).casefold() == value for cell in row if parse_value(cell) is None)
    number = parse_value(candidate)
    return number is not None and number == parse_value(computed['answer'])
