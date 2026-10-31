"""Generic HTML table rendering and parsing; no site- or task-specific layouts.

Flattening every <td> onto its own line destroys row identity: a 60-column
count table becomes thousands of one-token lines, evidence windows cut through
records, and models "repair" quotes by re-joining cells. Instead, each data
table becomes one delimited line per row with explicit block markers, so

* a record stays on one literal line that code can copy as a quotation;
* colspan/rowspan and multi-row headers are expanded into named columns;
* code can parse the same text back into rows for deterministic computation.

The rendered text is the tool observation itself, so quotations copied from
it remain literal source-observation spans. Header composition is a layout
interpretation: it does not establish what a column means semantically.
"""
from __future__ import annotations

import re

TABLE_START = re.compile(r'^\[TABLE (\d+): (\d+) rows x (\d+) columns\]$')
TABLE_END = '[END TABLE {}]'
_NUMBER = re.compile(r'^[\s+\-−–]?[\d.,\s]*\d[\d.,\s]*%?$')
MAX_COLUMNS = 80
MAX_CELL_CHARS = 300


def _cell_text(cell):
    text = ' '.join(cell.get_text(' ', strip=True).split())
    # The delimiter must stay unambiguous; a literal bar is extremely rare in data cells.
    return text.replace('|', '¦')[:MAX_CELL_CHARS]


def _is_numeric(text):
    import unicodedata
    return bool(text) and bool(_NUMBER.match(unicodedata.normalize('NFKC', text)))


def table_grid(table):
    """Expand spans into a rectangular grid of (text, is_header, continuation)."""
    rows = [row for row in table.find_all('tr') if row.find_parent('table') is table]
    grid, pending = [], {}
    for row in rows:
        cells = row.find_all(['th', 'td'], recursive=False)
        line, column = [], 0
        in_head = row.find_parent('thead') is not None
        iterator = iter(cells)
        while True:
            if column in pending:
                # A rowspan value applies to every covered row; only its own
                # colspan continuation columns are shown blank.
                text, header, remaining, sideways = pending[column]
                line.append((text, header, sideways))
                if remaining <= 1:
                    del pending[column]
                else:
                    pending[column] = (text, header, remaining - 1, sideways)
                column += 1
                continue
            cell = next(iterator, None)
            if cell is None:
                break
            text = _cell_text(cell)
            header = in_head or cell.name == 'th'
            try:
                span = max(1, min(int(cell.get('colspan', 1)), MAX_COLUMNS))
                down = max(1, min(int(cell.get('rowspan', 1)), 500))
            except (TypeError, ValueError):
                span, down = 1, 1
            for offset in range(span):
                line.append((text, header, offset > 0))
                if down > 1:
                    pending[column + offset] = (text, header, down - 1, offset > 0)
            column += span
        # A trailing rowspan can extend past the last explicit cell.
        while column in pending:
            text, header, remaining, sideways = pending.pop(column)
            line.append((text, header, sideways))
            if remaining > 1:
                pending[column] = (text, header, remaining - 1, sideways)
            column += 1
        if line:
            grid.append(line)
    return grid


def header_row_count(grid):
    count = 0
    for line in grid:
        if all(header for _, header, _ in line):
            count += 1
        else:
            break
    if count:
        return count if count < len(grid) else 0
    # Many sites style header rows with <td>. Accept up to three leading
    # non-numeric rows only when numeric data rows follow them.
    for index, line in enumerate(grid[:3]):
        if any(_is_numeric(text) for text, _, _ in line):
            return index if any(any(_is_numeric(t) for t, _, _ in later) for later in grid[index:]) else 0
    return 0


def render_table(table, index):
    grid = table_grid(table)
    if len(grid) < 2:
        return None
    width = max(len(line) for line in grid)
    if width < 2 or width > MAX_COLUMNS:
        return None
    heads = header_row_count(grid)
    columns = []
    for column in range(width):
        parts = []
        for line in grid[:heads]:
            text = line[column][0] if column < len(line) else ''
            if text and text not in parts:
                parts.append(text)
        columns.append(' '.join(parts))
    lines = [f'[TABLE {index}: {len(grid) - heads} rows x {width} columns]']
    if heads:
        lines.append('| ' + ' | '.join(columns) + ' |')
    for line in grid[heads:]:
        # Data colspans are shown once; repeating them would duplicate values.
        cells = ['' if continuation and not header else text for text, header, continuation in line]
        cells += [''] * (width - len(cells))
        lines.append('| ' + ' | '.join(cells) + ' |')
    lines.append(TABLE_END.format(index))
    return '\n'.join(lines)


def render_tables(soup):
    """Replace data tables in place; outer layout tables wrapping them are left as text."""
    tables = soup.find_all('table')
    tables.sort(key=lambda table: len(table.find_parents('table')), reverse=True)
    rendered = 0
    for table in tables:
        if table.find('table') is not None:
            continue  # contains a nested data table; treat as page layout
        block = render_table(table, rendered + 1)
        if block is None:
            continue
        rendered += 1
        table.replace_with(soup.new_string('\n' + block + '\n'))
    return rendered


def _split_row(line):
    line = line.strip()
    if len(line) < 2 or not (line.startswith('|') and line.endswith('|')):
        return None
    return [cell.strip() for cell in line[1:-1].split('|')]


def parse_table_blocks(text):
    """Parse rendered blocks back into rows. Incomplete blocks are marked, never padded."""
    blocks, lines = [], text.splitlines()
    index = 0
    while index < len(lines):
        match = TABLE_START.match(lines[index].strip())
        if not match:
            index += 1
            continue
        number, declared_rows, width = (int(x) for x in match.groups())
        end_marker = TABLE_END.format(number)
        body, cursor, complete = [], index + 1, False
        while cursor < len(lines):
            current = lines[cursor].strip()
            if current == end_marker:
                complete = True
                break
            if TABLE_START.match(current) or current.startswith('[Middle omitted') or current.startswith('[Separate original'):
                break
            body.append(current)
            cursor += 1
        rows = [cells for cells in map(_split_row, body) if cells is not None]
        # A header line exists only when one more line than declared data rows was rendered.
        header = rows[0] if len(rows) == declared_rows + 1 else None
        data = rows[1:] if header is not None else rows
        if any(len(row) != width for row in data) or len(data) != declared_rows:
            complete = False
        blocks.append({'table': number, 'columns': header or [f'column {i + 1}' for i in range(width)],
                       'has_header': header is not None, 'rows': data, 'complete': complete,
                       'lines': body})
        index = cursor + 1
    return blocks
