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
            ids.add(key.strip().casefold())
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
        '"groups":[{"species_key":"name or distinct morphological group","visual_features":"visible distinguishing traits",'
        '"location":"where in this frame","uncertain":false}]}]}. '
        'Mark uncertain true when identities cannot be separated. Do not output a count. '
        'Image timestamps, in order: '+json.dumps(stamps)+' Task: '+question,
        [p for _,p in frames],trace,'video_census_detail',json_output=True))
    count=census_count(report,stamps)
    trace.add('video_census_validated',report=report,maximum=count,scope='sampled-frame counts; species identities remain visual-model judgments')
    return json.dumps({'maximum_observed_species':count,'frames':report['frames'],
                       'limitation':'sampled frames only; not an exhaustive proof of the whole-video maximum'},ensure_ascii=False)


def temporal_neighbors(report, year, events):
    # Links can discover archives but their labels cannot establish roster facts.
    events=[dict(e,result=e.get('result','').split('\nNAVIGATION LINKS',1)[0]) for e in events]
    if report.get('year')!=year:raise ValueError('wrong requested year')
    source=report.get('source_url',''); time_quote=report.get('time_quote','')
    if not isinstance(time_quote,str) or not re.search(r'\b'+str(year)+r'\b',time_quote):
        raise ValueError('dated roster evidence required, not a current roster')
    validate_support([{'source_url':source,'quote':time_quote}],events)
    for e in events:
        if e.get('name')=='fetch_url' and e.get('result','').startswith('SOURCE: '+source+'\n'):
            dates=re.findall(r'UPDATE[^\n]*?(20\d{2}|19\d{2})',e['result'],re.I)
            if any(int(y)!=year for y in dates):raise ValueError('source update year contradicts requested period')
    rows=report.get('rows'); target=report.get('target_number')
    if type(target) is not int or not isinstance(rows,list):raise ValueError('numeric target and roster rows required')
    by_number={}
    for row in rows:
        n=row.get('number'); surname=row.get('surname'); quote=row.get('quote','')
        if type(n) is not int or n in by_number or not isinstance(surname,str) or not surname.strip():raise ValueError('invalid roster row')
        validate_support([{'source_url':source,'quote':quote}],events,[surname])
        if not re.search(r'(?<!\d)'+str(n)+r'(?!\d)',quote):raise ValueError('number missing from row evidence')
        if row.get('eligible') is not True:raise ValueError('row does not satisfy requested role')
        by_number[n]=surname
    if not all(n in by_number for n in (target-1,target,target+1)):raise ValueError('missing exact numeric neighbors')
    return by_number[target-1]+', '+by_number[target+1]


def solve_temporal_neighbors(agent,question,registry,trace):
    match=re.search(r'\bas of\s+(?:[A-Za-z]+\s+)?((?:19|20)\d{2})',question,re.I)
    if not match or not re.search(r'\bbefore\b.*\bafter\b',question,re.I) or not re.search(r'\bnumber',question,re.I):return None
    year=int(match[1])
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
    def historical_fetch(url):
        from .tools import fetch_url
        raw=fetch_url(url,link_query=str(year))
        dates=re.findall(r'UPDATE[^\n]*?(20\d{2}|19\d{2})',raw,re.I)
        if dates and any(int(y)!=year for y in dates):
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
        'follow relevant historical links, and try native-language queries if needed. '
        'Return ONLY JSON {"year":integer,"source_url":"fetched URL","time_quote":"literal heading or dated statement establishing roster period, not copyright",'
        '"target_number":integer,"rows":[{"number":integer,"surname":"Roman surname",'
        '"eligible":true,"quote":"literal source row containing number and surname"}]}. '
        'Include target and exact numeric neighbors; do not calculate final answer. '
        'Rows must come from the SAME dated roster. Preserve original text in quotes. '
        'If unavailable return {}. Task: '+question)
    messages=[{'role':'system','content':prompt}]
    for attempt,turns in enumerate((7,3)):
        raw=agent._run_tool_loop(messages,web,trace,turns,'subtask',
                                final_instruction='Return the historical roster JSON with literal quotes or {}.',final_json=True)
        report=read_json_object(raw)
        try:answer=temporal_neighbors(report,year,trace.events)
        except (ValueError,TypeError) as exc:
            trace.add('temporal_contract_rejected',reason=str(exc),report=report)
            messages.extend([{'role':'assistant','content':raw},{'role':'user','content':'Repair this dated-evidence requirement: '+str(exc)}])
            continue
        trace.add('temporal_contract_validated',report=report)
        return answer
    trace.add('temporal_contract_blocked',reason='dated neighbors not verified')
    return 'Unable to verify historical roster'
