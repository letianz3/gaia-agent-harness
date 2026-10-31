from pathlib import Path

from bs4 import BeautifulSoup

from gaia_agent.web_tables import parse_table_blocks, render_tables

FIXTURES = Path(__file__).parent / 'fixtures'


def rendered_text(html):
    soup = BeautifulSoup(html, 'html.parser')
    render_tables(soup)
    return '\n'.join(line.strip() for line in soup.get_text('\n').splitlines() if line.strip())


def test_columns_keep_meaning_on_one_literal_row():
    text = rendered_text('<h2>Approved May 2018</h2><table><tr><th>Project</th><th>Display date</th><th>Applicant</th></tr>'
                         '<tr><td><a href="/project">Example</a></td><td>June 2019</td><td>Alice</td></tr></table>')
    assert '| Project | Display date | Applicant |' in text
    assert '| Example | June 2019 | Alice |' in text
    [block] = parse_table_blocks(text)
    assert block['complete'] and block['rows'] == [['Example', 'June 2019', 'Alice']]


def test_spans_expand_without_duplicating_data_values():
    text = rendered_text('<table><tr><th>A</th><th>B</th></tr><tr><td colspan="2">Merged</td></tr>'
                         '<tr><td rowspan="2">x</td><td>1</td></tr><tr><td>2</td></tr></table>')
    [block] = parse_table_blocks(text)
    assert block['rows'] == [['Merged', ''], ['x', '1'], ['x', '2']]


def test_td_styled_multirow_headers_are_composed():
    text = rendered_text('<table><tr><td></td><td colspan="2">Total</td></tr><tr><td></td><td>m</td><td>w</td></tr>'
                         '<tr><td>AAA</td><td>3</td><td>-</td></tr></table>')
    [block] = parse_table_blocks(text)
    assert block['columns'] == ['', 'Total m', 'Total w'] and block['rows'] == [['AAA', '3', '-']]


def test_real_numbered_register_rows_stay_intact():
    text = rendered_text((FIXTURES / 'numbered_roster_table.html').read_text(encoding='utf-8'))
    assert '| １８ | 吉田 輝星 | 投 手 |' in text
    [block] = parse_table_blocks(text)
    assert block['complete'] and block['columns'] == ['背番号', '氏名', 'ポジション・役割']


def test_real_count_table_is_compact_and_complete():
    text = rendered_text((FIXTURES / 'olympic_counts_table.html').read_text(encoding='utf-8'))
    [block] = parse_table_blocks(text)
    assert block['complete'] and block['columns'][-1] == 'Total all'
    cuba = next(row for row in block['rows'] if row[0] == 'CUB')
    assert cuba[-1] == '1'
    assert len(text) < 15000


def test_nested_layout_table_keeps_inner_data_table():
    text = rendered_text('<table><tr><td><table><tr><th>K</th><th>V</th></tr><tr><td>a</td><td>1</td></tr></table></td></tr></table>')
    [block] = parse_table_blocks(text)
    assert block['rows'] == [['a', '1']]


def test_truncated_block_is_not_complete():
    text = rendered_text('<table><tr><th>K</th><th>V</th></tr>' + ''.join(f'<tr><td>r{i}</td><td>{i}</td></tr>' for i in range(5)) + '</table>')
    lines = text.splitlines()
    damaged = '\n'.join(lines[:4] + ['[Middle omitted; original passages follow]'] + lines[-1:])
    [block] = parse_table_blocks(damaged)
    assert not block['complete']


def test_fetch_url_renders_tables_and_keeps_links_found_inside_cells(monkeypatch):
    from types import SimpleNamespace

    import gaia_agent.tools as tools
    html = (b'<html><body><h1>2018 archive</h1><table><tr><th>Season</th><th>Register</th></tr>'
            b'<tr><td>2018</td><td><a href="/2018/register">2018 register</a></td></tr></table></body></html>')
    response = SimpleNamespace(is_redirect=False, iter_content=lambda **kw: iter([html]),
                               close=lambda: None, raise_for_status=lambda: None)
    monkeypatch.setattr(tools, '_validate_public_url', lambda u: u)
    monkeypatch.setattr(tools.requests, 'get', lambda *a, **k: response)
    raw = tools.fetch_url('https://example.org/archive', link_query='2018 register')
    assert '| 2018 | 2018 register |' in raw
    assert 'https://example.org/2018/register' in raw.split('NAVIGATION LINKS', 1)[1]
