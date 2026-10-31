import json
from pathlib import Path

from bs4 import BeautifulSoup

from gaia_agent.contracts import normalize_text, validate_support
from gaia_agent.resolution import (dated_source_valid, ground_numbered_rows, literal_numbered_records,
                                   temporal_neighbors, temporal_repair_message)
from gaia_agent.tracing import Trace
from gaia_agent.web_tables import render_tables

SOURCE = 'https://example.org/2023/register'
TITLE = '2023年度 Example 背番号一覧'


def fetched(body):
    return [dict(type='tool_call', name='fetch_url', succeeded=True, result='SOURCE: ' + SOURCE + '\n' + body)]


def test_fullwidth_digits_and_spaces_are_compatibility_equivalent_only():
    assert normalize_text('背番号: １８ 氏名: 吉田　輝星') == normalize_text('背番号: 18 氏名: 吉田 輝星')
    assert normalize_text('18 吉田') != normalize_text('19 吉田')
    validate_support([{'source_url': SOURCE, 'quote': '背番号: 18 氏名: 吉田 輝星'}], fetched('背番号:\n１８\n氏名:\n吉田　輝星\n'))


def test_labelled_blocks_pair_each_name_with_its_nearest_identifier():
    body = TITLE + '\n背番号:\n１８\n氏名:\n吉田　輝星\n役割:\n投　手\n背番号:\n１９\n氏名:\n玉井　大翔\n役割:\n投　手'
    assert literal_numbered_records(body, 18, '吉田 輝星') == {'１８\n氏名:\n吉田　輝星'}
    assert literal_numbered_records(body, 19, '吉田 輝星') == set()


def test_rendered_table_rows_are_copied_as_one_literal_line():
    html = (Path(__file__).parent / 'fixtures' / 'numbered_roster_table.html').read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')
    render_tables(soup)
    body = '\n'.join(line.strip() for line in soup.get_text('\n').splitlines() if line.strip())
    events = fetched(body)
    report = dict(year=2023, source_url=SOURCE, time_quote='reworded', target_number=19, rows=[
        dict(number=n, surname=s, eligible=True, native_name=nm, quote=f'背番号: {n} 氏名: {nm}')
        for n, s, nm in ((18, 'Yoshida', '吉田 輝星'), (19, 'Tamai', '玉井 大翔'), (20, 'Uehara', '上原 健太'))])
    fixed = ground_numbered_rows(report, events, 2023)
    assert fixed['rows'][0]['quote'] == '| １８ | 吉田 輝星 | 投 手 |'
    assert '2023' in fixed['time_quote']
    assert temporal_neighbors(fixed, 2023, events, check_names=False) == 'Yoshida, Uehara'


def test_repair_keeps_an_established_dated_source_and_shows_literal_rows():
    body = TITLE + '\n| 背番号 | 氏名 |\n| １８ | 吉田 輝星 |\n| １９ | 玉井 大翔 |\n| ２０ | 上原 健太 |'
    trace = Trace(task_id='t', question='q')
    trace.events.extend(fetched(body))
    report = dict(year=2023, source_url=SOURCE, time_quote=TITLE, target_number=19, rows=[])
    assert dated_source_valid(report, 2023, trace.events)
    message = temporal_repair_message(ValueError('quotation absent from retrieved page body'), report, report, 'q', 2023, trace)
    assert 'KEEP this source_url' in message and '| １８ | 吉田 輝星 |' in message
    assert 'Do NOT repeat' not in message and 'Do not re-open current rosters' not in message
    undated = dict(report, time_quote='現役選手の一覧')
    assert not dated_source_valid(undated, 2023, trace.events)
    fallback = temporal_repair_message(ValueError('dated roster evidence required'), undated, None, 'q', 2023, trace)
    assert 'ESTABLISHED SOURCE' not in fallback and json.dumps(SOURCE)[1:-1] in fallback


def test_far_table_rows_keep_their_literal_header_span():
    from gaia_agent.evidence import relevant_excerpt
    rows = '\n'.join(f'| Item {i} | {i} | filler text for spacing |' for i in range(80))
    body = 'Report\n' + 'preamble words ' * 40 + '\n[TABLE 1: 80 rows x 3 columns]\n| Project | Display date | Applicant |\n' + rows + '\n[END TABLE 1]'
    excerpt, _ = relevant_excerpt(body, ('Which applicant got Item 71?', 'Item 71'), 1800)
    assert '| Project | Display date | Applicant |' in excerpt and '| Item 71 | 71 |' in excerpt


def test_blocked_roster_keeps_only_a_provenance_level_fallback():
    from gaia_agent.resolution import ranked_fallback
    body = TITLE + '\n| 背番号 | 氏名 |\n| １８ | 吉田 輝星 |\n| １９ | 玉井 大翔 |\n| ２０ | 上原 健太 |'
    events = fetched(body)
    rows = [dict(number=n, surname=s, eligible=True, native_name=nm, quote=f'| {n} | {nm} |')
            for n, s, nm in ((18, 'Yoshida', '吉田 輝星'), (19, 'Tamai', '玉井 大翔'), (20, 'Uehara', '上原 健太'))]
    report = dict(year=2023, source_url=SOURCE, time_quote=TITLE, target_number=19, rows=rows)
    best = ranked_fallback(None, report, 'one bilingual quotation must join the full original name and Roman surname', 2023, events)
    assert best[:2] == (0, 'Yoshida, Uehara')
    assert ranked_fallback(None, report, 'missing exact numeric neighbors', 2023, events) is None
    assert ranked_fallback(None, report, 'row does not satisfy requested role', 2023, events) is None
