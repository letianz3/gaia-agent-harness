"""Evidence resolution: item-level context, temporal joins and visual censuses."""
import json
import re
from .contracts import evidence_windows, validate_support
from .evidence import read_json_object


def item_evidence(events, items):
    pages=[e for e in events if e.get('type')=='tool_call' and e.get('name')=='fetch_url'
           and e.get('succeeded') and e.get('result','').startswith('SOURCE: ')]
    records=[]
    for item in items:
        excerpts=[]
        for e in pages:
            source,body=e['result'].split('\n',1)
            for quote in evidence_windows(body,item,limit=2):
                excerpts.append({'source':source[8:],'quote':quote})
            if len(excerpts)>=3:break
        records.append({'item':item,'excerpts':excerpts[:3]})
    return json.dumps(records,ensure_ascii=False)


def census_identity(group):
    """Normalize formatting and explicit life-stage annotations, not taxonomy.

    Never stem species names or merge by broad family/common-name resemblance.
    Plain names are preserved; stage suffixes require an annotation delimiter.
    """
    key = group.get('species_key')
    if not isinstance(key, str) or not key.strip():
        raise ValueError('species identity required')
    key = key.strip().casefold()
    stage = r'(?:adult|chick|juvenile|immature|fledgling)s?'
    if re.fullmatch(stage, key):
        raise ValueError('life stage alone is not a species identity')
    key = re.sub(r'\s*\(' + stage + r'\)\s*$', '', key)
    key = re.sub(r'[_:]' + stage + r'$', '', key)
    key = re.sub(r'[_\s]+', ' ', key).strip()
    if not key:
        raise ValueError('life stage alone is not a species identity')
    return key


def census_count(report, timestamps):
    frames=report.get('frames')
    if not isinstance(frames,list) or not frames:raise ValueError('frame census required')
    counts=[]; seen=set()
    for frame in frames:
        t=frame.get('timestamp'); groups=frame.get('groups')
        if t not in timestamps or t in seen:raise ValueError('unknown or duplicate timestamp')
        seen.add(t)
        if not isinstance(groups,list):raise ValueError('groups required')
        ids=set()
        for group in groups:
            key=group.get('species_key')
            if not isinstance(key,str) or not key.strip() or not group.get('visual_features') or not group.get('location'):
                raise ValueError('each group needs identity, visible features and location')
            if group.get('uncertain') is not False:raise ValueError('unresolved visual identity')
            ids.add(census_identity(group))
        counts.append(len(ids))
    if seen!=set(timestamps):raise ValueError('every inspected frame needs a census')
    return max(counts)


CENSUS_CANDIDATES_PER_SHEET = 2
CENSUS_FRAMES_PER_CALL = 6


def inspect_census(agent, question, sheets, video_path, media_dir, trace):
    """Locate candidate frames, then inventory each frame independently in small batches.

    Recall of small or background species depends on which frames are inspected,
    so each sheet nominates up to two distinct candidates; precision is kept by
    requiring identity, visible features and location per group in every frame.
    """
    from .media_tools import video_detail_frames
    times=[]
    for sheet in sheets[:6]:
        proposal=read_json_object(agent._vision_observation(
        'Locate up to TWO frames on THIS sheet with the most DISTINCT species, preferring frames that differ '
        'in which species are visible, including small or background birds. '
        'Do not count all members of a broad animal group as one species; age/sex differences '
        'alone do not establish separate species. Return JSON {"timestamps":[seconds],"reason":"visible differences"}. '
        'Use timestamps printed on the sheet. Inspect every cell before choosing. Task: '+question,[sheet],trace,'video_census_scan',json_output=True))
        candidates=proposal.get('timestamps',[])
        if isinstance(candidates,list):
            times.extend(t for t in candidates[:CENSUS_CANDIDATES_PER_SHEET] if isinstance(t,(int,float)))
    times=sorted(set(times))
    if not times:raise ValueError('candidate timestamps missing')
    frames=video_detail_frames(video_path,media_dir,times,limit=CENSUS_CANDIDATES_PER_SHEET*6)
    reports=[]
    for start in range(0,len(frames),CENSUS_FRAMES_PER_CALL):
        batch=frames[start:start+CENSUS_FRAMES_PER_CALL]
        stamps=[t for t,_ in batch]
        report=read_json_object(agent._vision_observation(
            'Inspect each individual frame independently. Inventory DISTINCT species visible simultaneously, '
            'including small background individuals. Use the same species_key for adults/chicks of the '
            'same species; different species within a broad group need separate keys and distinguishing '
            'features. Do not merge solely because both are penguins, ducks, gulls, etc. Do not add '
            'species merely heard or seen in another frame. Return JSON {"frames":[{"timestamp":number,'
            '"groups":[{"species_key":"canonical species name ONLY, never age/sex/individual ID","life_stage":"adult/chick/juvenile/unknown",'
            '"visual_features":"visible distinguishing traits",'
            '"location":"where in this frame","uncertain":false}]}]}. '
            'Mark uncertain true when identities cannot be separated. Do not output a count. '
            'Image timestamps, in order: '+json.dumps(stamps)+' Task: '+question,
            [p for _,p in batch],trace,'video_census_detail',json_output=True))
        census_count(report,stamps)  # validate every batch on its own timestamps
        reports.extend(report['frames'])
    merged={'frames':reports}
    count=census_count(merged,[t for t,_ in frames])
    trace.add('video_census_validated',report=merged,maximum=count,scope='sampled-frame counts; species identities remain visual-model judgments')
    return json.dumps({'maximum_observed_species':count,'frames':merged['frames'],
                       'limitation':'sampled frames only; not an exhaustive proof of the whole-video maximum'},ensure_ascii=False)


def temporal_source_conflict(raw, year):
    """A recent update does not invalidate an explicitly dated retrospective roster."""
    body=raw.split('\nNAVIGATION LINKS',1)[0]
    dates=re.findall(r'UPDATE[^\n]*?(20\d{2}|19\d{2})',body,re.I)
    if not any(int(y)!=year for y in dates):return False
    dated_section=re.search(r'(?m)^[^\n]{0,100}(?<!\d)'+str(year)+
                            r'(?!\d)[^\n]{0,100}\b(?:roster|register|lineup)\b[^\n]{0,60}$',body,re.I)
    reverse_section=re.search(r'(?m)^[^\n]{0,60}\b(?:roster|register|lineup)\b[^\n]{0,100}(?<!\d)'+
                              str(year)+r'(?!\d)[^\n]{0,60}$',body,re.I)
    return not bool(dated_section or reverse_section)


def validate_name_bridge(row, events):
    quotes=validate_support(row.get('name_support'),events)
    from .contracts import canonical
    native=re.sub(r'\s+','',canonical(row['native_name'])).casefold()
    roman=canonical(row['surname']).casefold()
    if not any(native in re.sub(r'\s+','',q) and roman in q for q in quotes):
        raise ValueError('one bilingual quotation must join the full original name and Roman surname')


def temporal_neighbors(report, year, events, *, check_names=True):
    # Links can discover archives but their labels cannot establish roster facts.
    events=[dict(e,result=e.get('result','').split('\nNAVIGATION LINKS',1)[0]) for e in events]
    if report.get('year')!=year:raise ValueError('wrong requested year')
    source=report.get('source_url',''); time_quote=report.get('time_quote','')
    from .contracts import canonical
    if not isinstance(time_quote,str) or not re.search(r'(?<!\d)'+str(year)+r'(?!\d)',canonical(time_quote)):
        raise ValueError('dated roster evidence required, not a current roster')
    validate_support([{'source_url':source,'quote':time_quote}],events)
    for e in events:
        if e.get('name')=='fetch_url' and e.get('result','').startswith('SOURCE: '+source+'\n'):
            if temporal_source_conflict(e['result'],year):raise ValueError('source update year contradicts requested period')
    rows=report.get('rows'); target=report.get('target_number')
    if type(target) is not int or not isinstance(rows,list):raise ValueError('numeric target and roster rows required')
    by_number={}
    for row in rows:
        n=row.get('number'); surname=row.get('surname'); quote=row.get('quote','')
        if type(n) is not int or n in by_number or not isinstance(surname,str) or not surname.strip():raise ValueError('invalid roster row')
        native=row.get('native_name')
        if not check_names:
            # The extraction stage may omit native_name. Validate row provenance
            # first; full-name extraction and strict identity checks follow.
            validate_support([{'source_url':source,'quote':quote}],events,min_quote_length=6)
        elif native and native != surname:
            validate_support([{'source_url':source,'quote':quote}],events,[native],min_quote_length=6)
            # A translation is an identity join, not permission to invent a name.
            if check_names:
                validate_name_bridge(row,events)
        else:
            validate_support([{'source_url':source,'quote':quote}],events,[surname])
        from .contracts import canonical
        if not re.search(r'(?<!\d)'+str(n)+r'(?!\d)',canonical(quote)):raise ValueError('number missing from row evidence')
        if row.get('eligible') is not True:raise ValueError('row does not satisfy requested role')
        by_number[n]=surname
    if not all(n in by_number for n in (target-1,target,target+1)):raise ValueError('missing exact numeric neighbors')
    return by_number[target-1]+', '+by_number[target+1]


def literal_name_bridge(events, native, surname):
    """Copy a nearby bilingual span verbatim instead of asking a model to quote it."""
    for event in events:
        raw=event.get('result','')
        if event.get('name')!='fetch_url' or not event.get('succeeded') or not raw.startswith('SOURCE: '):continue
        source,body=raw.split('\n',1)
        body=body.split('\nNAVIGATION LINKS',1)[0].split('\n\nHARNESS SOURCE CHECK',1)[0]
        chars=[];positions=[]
        for index,char in enumerate(body):
            if not char.isspace():
                chars.extend(char.casefold());positions.extend([index]*len(char.casefold()))
        compact=''.join(chars)
        left=re.sub(r'\s+','',native).casefold();right=re.sub(r'\s+','',surname).casefold()
        for match in re.finditer(re.escape(left),compact):
            for other in re.finditer(re.escape(right),compact):
                a=min(match.start(),other.start());b=max(match.end(),other.end())
                start=max(0,positions[a]-40);end=min(len(body),positions[b-1]+41)
                if end-start<=800:
                    return [{'source_url':source[8:],'quote':body[start:end]}]
    return []


def resolve_roster_names(agent, report, registry, trace):
    """Resolve only name rendering after historical row provenance has passed."""
    from .contracts import ask_json
    identities=ask_json(agent,'Extract the FULL ORIGINAL-SCRIPT PERSON NAME from each literal roster row. '
        'Do not return only a surname, translate, add characters or return a role label. '
        'Return {"names":[{"number":integer,"native_name":"exact full name from row"}]}. Rows: '+
        json.dumps([{'number':r['number'],'quote':r['quote']} for r in report['rows']],ensure_ascii=False),trace)
    names=identities.get('names',[])
    if isinstance(names,list):
        for item in names:
            if not isinstance(item,dict):continue
            for row in report['rows']:
                value=item.get('native_name')
                if row['number']==item.get('number') and isinstance(value,str) and len(value)>1 and value in row['quote']:
                    row['native_name']=value
    for row in report['rows']:
        native=row.get('native_name');surname=row.get('surname')
        if not native or native==surname:continue
        try:
            validate_name_bridge(row,trace.events)
            continue
        except ValueError:pass
        row['name_support']=literal_name_bridge(trace.events,native,surname)
        search_name=re.sub(r'(?<=[\u3400-\u9fff])\s+(?=[\u3400-\u9fff])','',native)
        for query in (f'{search_name} {surname}',f'{search_name} {surname} Wikipedia'):
            if row['name_support']:break
            args=json.dumps({'query':query})
            raw,ok=registry.execute('search_web',args)
            trace.record_tool_call()
            trace.add('tool_call',name='search_web',arguments=args,result=raw,succeeded=ok,phase='identity_bridge')
            try:results=json.loads(raw) if ok else []
            except ValueError:results=[]
            if not isinstance(results,list):results=[]
            for result in results[:2]:
                url=result.get('url') if isinstance(result,dict) else None
                if not isinstance(url,str):continue
                args=json.dumps({'url':url})
                body,success=registry.execute('fetch_url',args)
                trace.record_tool_call()
                trace.add('tool_call',name='fetch_url',arguments=args,result=body,succeeded=success,phase='identity_bridge')
                row['name_support']=literal_name_bridge(trace.events,native,surname)
                if row['name_support']:break
    return report


_NUMBER_LINE = re.compile(r'(?:[^\d:：]{0,24}[:：])?\s*(?:no\.?|#)?\s*(\d{1,4})', re.I)


def _compact(text):
    from .contracts import canonical
    return re.sub(r'\s+', '', canonical(text)).casefold()


def _number_token(text):
    from .contracts import canonical
    match = _NUMBER_LINE.fullmatch(canonical(text).strip())
    return int(match[1]) if match else None


def _name_line(text, name):
    """The line is the name, optionally preceded by a short field label."""
    compact = _compact(text)
    if compact == name:
        return True
    head, _, tail = re.sub(r'：', ':', compact).rpartition(':')
    return tail == name and 0 < len(head) <= 24


def literal_numbered_records(body, number, native):
    """Literal spans pairing an identifier with a name, independent of page layout.

    Supported generically: rendered table rows (one record per line), plain
    alternating identifier/name lines, and labelled field blocks. The pairing
    uses the NEAREST identifier to the name; a different nearer identifier, or
    an equally near conflicting one, means the claimed pair is not observed.
    """
    from .web_tables import _split_row
    name = _compact(native)
    if not name:
        return set()
    lines = body.splitlines()
    found = set()
    for index, line in enumerate(lines):
        cells = _split_row(line)
        if cells is not None:
            if (any(_number_token(cell) == number for cell in cells)
                    and any(_compact(cell) == name for cell in cells)):
                found.add(line)
            continue
        if not _name_line(line, name):
            continue
        nearest = []
        for step in (-1, 1):
            for distance in range(1, 5):
                other = index + step * distance
                if not 0 <= other < len(lines) or _split_row(lines[other]) is not None:
                    break
                value = _number_token(lines[other])
                if value is not None:
                    nearest.append((distance, value, other))
                    break
        if not nearest:
            continue
        best = min(distance for distance, _, _ in nearest)
        closest = [(value, other) for distance, value, other in nearest if distance == best]
        if len({value for value, _ in closest}) > 1:
            closest = [item for item in closest if (item[1] < index) == _identifier_first(lines, index)]
        if len(closest) == 1 and closest[0][0] == number:
            other = closest[0][1]
            found.add('\n'.join(lines[min(index, other):max(index, other) + 1]))
    return found


def _identifier_first(lines, index):
    """Orientation of an alternating identifier/name run, read from where it ends.

    Headings usually precede a list, so the run's END is the reliable edge: a run
    ending in a name pairs identifiers with the following name, and vice versa.
    """
    cursor = index
    while (cursor + 1 < len(lines) and (_number_token(lines[cursor]) is None)
           != (_number_token(lines[cursor + 1]) is None)):
        cursor += 1
    return _number_token(lines[cursor]) is None


def _record_name(quote, native):
    from .web_tables import _split_row
    name = _compact(native)
    cells = _split_row(quote)
    if cells is not None:
        return next(cell for cell in cells if _compact(cell) == name)
    line = next(line for line in quote.splitlines() if _name_line(line, name))
    return re.split(r'[:：]', line)[-1].strip() if _compact(line) != name else line.strip()


def ground_numbered_rows(report, events, year):
    """Copy uniquely observed number/name records; never repair unknown facts.

    Layout handling lives in literal_numbered_records. It cannot infer roles or
    translate identities; it only replaces model-written quotations with the
    unique literal record that already pairs the claimed number and name.
    """
    import copy
    result = copy.deepcopy(report)
    source = result.get('source_url')
    bodies = [e['result'].split('\n', 1)[1].split('\nNAVIGATION LINKS', 1)[0]
              for e in events if e.get('name') == 'fetch_url' and e.get('succeeded')
              and e.get('result', '').startswith('SOURCE: ' + str(source) + '\n')]
    if not bodies:
        return result
    try:
        validate_support([dict(source_url=source, quote=result.get('time_quote', ''))], events)
    except (ValueError, TypeError):
        # A literal dated document title, not a fabricated combined heading.
        titles = {body.splitlines()[0].strip() for body in bodies if body.splitlines()}
        titles = {title for title in titles if re.search(r'(?<!\d)' + str(year) + r'(?!\d)', title)
                  and 12 <= len(title) <= 250 and not re.search(r'copyright|update|©', title, re.I)}
        if len(titles) == 1:
            result['time_quote'] = titles.pop()
    rows = result.get('rows', [])
    if not isinstance(rows, list):
        return result
    for row in rows:
        if not isinstance(row, dict):
            continue
        native = row.get('native_name')
        number = row.get('number')
        if not isinstance(native, str) or not native.strip() or type(number) is not int:
            continue
        matches = set().union(*(literal_numbered_records(body, number, native) for body in bodies))
        if len(matches) == 1:
            row['quote'] = matches.pop()
            row['native_name'] = _record_name(row['quote'], native)
    return result


def source_record_lines(events, source, numbers, limit=12):
    """Literal lines from an already validated source near the requested identifiers."""
    lines = []
    for event in events:
        raw = event.get('result', '')
        if event.get('name') != 'fetch_url' or not event.get('succeeded') or not raw.startswith('SOURCE: ' + str(source) + '\n'):
            continue
        body = raw.split('\n', 1)[1].split('\nNAVIGATION LINKS', 1)[0].splitlines()
        from .web_tables import _split_row
        for index, line in enumerate(body):
            cells = _split_row(line)
            tokens = [_number_token(cell) for cell in cells] if cells is not None else [_number_token(line)]
            if any(token in numbers for token in tokens if token is not None):
                span = line if cells is not None else '\n'.join(body[index:index + 4])
                if span not in lines:
                    lines.append(span)
        if lines:
            break
    return lines[:limit]


# Rejections about how rows were QUOTED do not make the dated source wrong.
PROVENANCE_ERRORS=('quotation absent','number missing from row evidence','does not mention required entity',
                   'bilingual quotation','invalid roster row','subject heading')


def dated_source_valid(report, year, events):
    """The source period is established, independent of whether rows were quoted well."""
    if not isinstance(report,dict) or report.get('year')!=year:return False
    source=report.get('source_url','');time_quote=report.get('time_quote','')
    from .contracts import canonical
    if not isinstance(time_quote,str) or not re.search(r'(?<!\d)'+str(year)+r'(?!\d)',canonical(time_quote)):return False
    try:validate_support([{'source_url':source,'quote':time_quote}],events)
    except (ValueError,TypeError):return False
    bodies=[e['result'] for e in events if e.get('name')=='fetch_url' and e.get('succeeded')
            and e.get('result','').startswith('SOURCE: '+str(source)+'\n')]
    return bool(bodies) and not any(temporal_source_conflict(raw,year) for raw in bodies)


def ranked_fallback(current, report, reason, year, events):
    """Keep the least severe rejected candidate whose dated source is verified.

    Severity 0: row provenance passed, only the bilingual name bridge failed.
    Severity 1: rows were not quoted literally. Role, neighbor and period
    failures never produce a fallback: they mean the answer itself is unsupported.
    """
    if not any(marker in reason for marker in PROVENANCE_ERRORS):
        return current
    rows=report.get('rows'); target=report.get('target_number')
    if not isinstance(rows,list) or type(target) is not int:
        return current
    names={r.get('number'):r.get('surname') for r in rows if isinstance(r,dict)}
    before,after=names.get(target-1),names.get(target+1)
    if not all(isinstance(x,str) and re.fullmatch(r"[A-Za-z][A-Za-z' -]*",x.strip() or '-') for x in (before,after)):
        return current
    try:
        temporal_neighbors(report,year,events,check_names=False)
        severity=0
    except (ValueError,TypeError):
        severity=1
    candidate=(severity,before.strip()+', '+after.strip(),reason)
    return candidate if current is None or severity<=current[0] else current


def temporal_repair_message(exc, report, pinned, question, year, trace):
    """Repair from the established source; never tell the model to abandon it."""
    from .evidence import evidence_packet
    reason=str(exc)
    completed=[{'tool':e.get('name'),'arguments':e.get('arguments'),'ok':e.get('succeeded')}
               for e in trace.events if e.get('type')=='tool_call']
    text=('Repair this dated-evidence requirement: '+reason+
          '\nThese requests already ran; do not re-run them, but you MAY and SHOULD still cite any source '
          'they fetched: '+json.dumps(completed,ensure_ascii=False))
    if pinned is not None:
        target=pinned.get('target_number')
        numbers={target-1,target,target+1} if type(target) is int else set()
        lines=source_record_lines(trace.events,pinned['source_url'],numbers)
        text+=('\nESTABLISHED SOURCE: '+pinned['source_url']+' is already fetched and its period quote "'+
               str(pinned.get('time_quote'))+'" was verified for '+str(year)+'. KEEP this source_url and time_quote; '
               'do not search for another roster. '+
               ('Fix only the row quotations by copying these literal source lines exactly (including '
                'full-width characters): '+json.dumps(lines,ensure_ascii=False) if lines else
                'Copy row quotations exactly from its observed text.'))
        if not any(marker in reason for marker in PROVENANCE_ERRORS):
            text+=('\nThe remaining problem concerns the rows themselves (role or neighbors), not the period. '
                   'Use the same source if it lists the needed numbers.')
    else:
        text+=('\nExisting observations: '+evidence_packet(trace.events,focus=(question,))+
               '\nIf an English historical roster was not found, switch to a native-language year-specific '
               'roster query, then obtain bilingual identity evidence. Do not re-open current rosters.')
    return text


def solve_temporal_neighbors(agent,question,registry,trace):
    from .policies import historical_neighbor_year
    year=historical_neighbor_year(question)
    if year is None:return None
    from .registry import ToolRegistry
    web=ToolRegistry()
    web.audit=registry.audit
    def historical_search(query):
        if str(year) not in query:query+=' '+str(year)
        raw,ok=registry.execute('search_web',json.dumps({'query':query}))
        if not ok:raise ValueError(raw)
        try:
            rows=json.loads(raw)
            if isinstance(rows,list):
                rows.sort(key=lambda r:str(year) not in (r.get('title','')+' '+r.get('url','')))
                return json.dumps(rows,ensure_ascii=False)
        except ValueError:pass
        return raw
    def historical_fetch(url,link_query=None):
        from .tools import fetch_url
        raw=fetch_url(url,link_query=link_query or str(year))
        dates=re.findall(r'UPDATE[^\n]*?(20\d{2}|19\d{2})',raw,re.I)
        if temporal_source_conflict(raw,year):
            links=raw.split('NAVIGATION LINKS',1)[-1] if 'NAVIGATION LINKS' in raw else ''
            raise ValueError('Historical constraint: this page explicitly updates to '+','.join(dates)+
                             ', not '+str(year)+'. Open a year-specific source; do not retry this current roster. Navigation only: '+links)
        return raw
    for schema in registry.schemas():
        f=schema['function']
        if f['name'] in ('search_web','fetch_url'):
            web.register(f['name'],f['description'],f['parameters'],
                         historical_search if f['name']=='search_web' else historical_fetch,parallel_safe=True)
    prompt=('Find the HISTORICAL roster needed by the question, never substitute today\'s roster. '
        'Use an official season-specific register or archived page; a reputable historical register is also acceptable. '
        'Prioritize results whose title or URL explicitly includes the year. Follow navigation links to season archives; do not invent URLs. Avoid repeating identical failed searches. Search with the target year, '
        'follow relevant historical links. For non-English teams/institutions, search in their native language EARLY '
        '(native organization name + year + local words for roster and uniform/identifier number). '
        'Do not require the roster itself to be in English. A dated native-language season register is useful evidence. '
        'Return ONLY JSON {"year":integer,"source_url":"fetched URL","time_quote":"literal heading or dated statement establishing roster period, not copyright",'
        '"target_number":integer,"rows":[{"number":integer,"surname":"Roman surname",'
        '"eligible":true,"quote":"literal source row containing number and original name",'
        '"native_name":"FULL original-script person name if different from Roman surname",'
        '"name_support":[{"source_url":"fetched bilingual profile URL","quote":"literal text linking original and Roman names"}]}]}. '
        'Include target and exact numeric neighbors; do not calculate final answer. '
        'Rows must come from the SAME dated roster. Preserve original text in quotes. '
        'For translated names, fetch a bilingual profile linking the original surname and Roman surname; '
        'do not translate quotations or invent transliterations. Name profiles may be current: they establish identity only, '
        'while the dated roster establishes past numbers and roles. '
        'If unavailable return {}. Task: '+question)
    from .contracts import ask_json
    discovery=ask_json(agent,
        'Generate at most TWO search queries to locate a historical numbered roster. '
        'One English query and one in the native language of the relevant organization. '
        'Include organization identity, requested year and local terms for roster/uniform numbers. '
        'Do not guess answers, player neighbors or URLs. Never invent native-script spelling of a Roman name; '
        'retain its Roman spelling if uncertain. Return {"queries":["...","..."]}. Task: '+question,trace)
    observations=[]
    queries=discovery.get('queries',[])
    if isinstance(queries,list):
        for query in queries[:2]:
            if not isinstance(query,str) or not query.strip() or len(query)>500:continue
            args=json.dumps({'query':query})
            result,ok=web.execute('search_web',args)
            trace.record_tool_call()
            trace.add('tool_call',name='search_web',arguments=args,result=result,succeeded=ok,phase='historical_discovery')
            observations.append({'query':query,'results':result})
    messages=[{'role':'system','content':prompt},
              {'role':'user','content':'Discovery results only (fetch sources before citing): '+json.dumps(observations,ensure_ascii=False)}]
    pinned=None
    fallback=None
    for attempt,turns in enumerate((8,6,4)):
        raw=agent._run_tool_loop(messages,web,trace,turns,'subtask',
                                final_instruction='Return the historical roster JSON with literal quotes or {}.',final_json=True)
        report=read_json_object(raw)
        grounded = ground_numbered_rows(report, trace.events, year)
        if grounded != report:
            trace.add('temporal_source_materialized', report=grounded,
                      scope='literal title and unique number/name spans; identity still requires validation')
        report = grounded
        try:
            temporal_neighbors(report,year,trace.events,check_names=False)
            report=resolve_roster_names(agent,report,registry,trace)
            answer=temporal_neighbors(report,year,trace.events)
        except (ValueError,TypeError) as exc:
            trace.add('temporal_contract_rejected',reason=str(exc),report=report)
            if dated_source_valid(report,year,trace.events):
                pinned=report
                fallback=ranked_fallback(fallback,report,str(exc),year,trace.events)
            messages.extend([{'role':'assistant','content':raw},
                             {'role':'user','content':temporal_repair_message(exc,report,pinned,question,year,trace)}])
            continue
        trace.add('temporal_contract_validated',report=report)
        return answer
    trace.add('temporal_contract_blocked',reason='dated neighbors not verified')
    if fallback is not None:
        severity,answer,reason=fallback
        trace.add('temporal_best_effort',answer=answer,severity=severity,reason=reason,
                  scope='dated source verified; only row/name provenance unresolved')
        return answer
    return None  # defer to the general pipeline instead of abstaining
