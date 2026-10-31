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


def inspect_census(agent, question, sheets, video_path, media_dir, trace):
    from .media_tools import video_detail_frames
    times=[]
    for sheet in sheets[:6]:
        proposal=read_json_object(agent._vision_observation(
        'Locate ONE frame on THIS sheet with the most DISTINCT species and ambiguous overlaps. '
        'Do not count all members of a broad animal group as one species; age/sex differences '
        'alone do not establish separate species. Return JSON {"timestamps":[seconds],"reason":"visible differences"}. '
        'Use timestamps printed on the sheet. Inspect every cell before choosing. Task: '+question,[sheet],trace,'video_census_scan',json_output=True))
        candidates=proposal.get('timestamps',[])
        if isinstance(candidates,list):times.extend(candidates[:1])
    if not isinstance(times,list) or not times:raise ValueError('candidate timestamps missing')
    frames=video_detail_frames(video_path,media_dir,times[:6])
    stamps=[t for t,_ in frames]
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
        [p for _,p in frames],trace,'video_census_detail',json_output=True))
    count=census_count(report,stamps)
    trace.add('video_census_validated',report=report,maximum=count,scope='sampled-frame counts; species identities remain visual-model judgments')
    return json.dumps({'maximum_observed_species':count,'frames':report['frames'],
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
    native=re.sub(r'\s+','',row['native_name']).casefold()
    roman=row['surname'].casefold()
    if not any(native in re.sub(r'\s+','',q) and roman in q for q in quotes):
        raise ValueError('one bilingual quotation must join the full original name and Roman surname')


def temporal_neighbors(report, year, events, *, check_names=True):
    # Links can discover archives but their labels cannot establish roster facts.
    events=[dict(e,result=e.get('result','').split('\nNAVIGATION LINKS',1)[0]) for e in events]
    if report.get('year')!=year:raise ValueError('wrong requested year')
    source=report.get('source_url',''); time_quote=report.get('time_quote','')
    if not isinstance(time_quote,str) or not re.search(r'(?<!\d)'+str(year)+r'(?!\d)',time_quote):
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
        if not re.search(r'(?<!\d)'+str(n)+r'(?!\d)',quote):raise ValueError('number missing from row evidence')
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
    for attempt,turns in enumerate((8,6,4)):
        raw=agent._run_tool_loop(messages,web,trace,turns,'subtask',
                                final_instruction='Return the historical roster JSON with literal quotes or {}.',final_json=True)
        report=read_json_object(raw)
        try:
            temporal_neighbors(report,year,trace.events,check_names=False)
            report=resolve_roster_names(agent,report,registry,trace)
            answer=temporal_neighbors(report,year,trace.events)
        except (ValueError,TypeError) as exc:
            trace.add('temporal_contract_rejected',reason=str(exc),report=report)
            from .evidence import evidence_packet
            completed=[{'tool':e.get('name'),'arguments':e.get('arguments'),'ok':e.get('succeeded')}
                       for e in trace.events if e.get('type')=='tool_call']
            messages.extend([{'role':'assistant','content':raw},{'role':'user','content':
                'Repair this dated-evidence requirement: '+str(exc)+
                '\nDo NOT repeat these completed searches/URLs: '+json.dumps(completed,ensure_ascii=False)+
                '\nExisting observations: '+evidence_packet(trace.events,focus=(question,))+
                '\nIf an English historical roster was not found, switch to a native-language year-specific '
                'roster query, then obtain bilingual identity evidence. Do not re-open current rosters.'}])
            continue
        trace.add('temporal_contract_validated',report=report)
        return answer
    trace.add('temporal_contract_blocked',reason='dated neighbors not verified')
    return 'Unable to verify historical roster'
