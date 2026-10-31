"""Bounded raw evidence for synthesis and independent verification."""
import json
import re
import unicodedata


def _canonical_space(text):
    return ' '.join(unicodedata.normalize('NFKC', text).split())


def read_json_object(raw):
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip(), flags=re.I)
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def materialize_support(report, evidence):
    """The model selects evidence IDs; code copies the original source spans.

    Selection proves provenance only. The critic still judges entailment, date,
    identity and coverage; valid IDs alone never upgrade its verdict.
    """
    if 'evidence_ids' not in report:
        return report
    report = dict(report)
    report['support'] = []
    ids = report.get('evidence_ids')
    try:
        records = {row['id']: row for row in map(json.loads, evidence.splitlines())}
        if not isinstance(ids, list) or not ids or len(ids) > 12:
            return report
        for key in ids:
            if not isinstance(key, str) or key not in records or records[key]['kind'] not in {'observation', 'task_input'}:
                return {**report, 'support': []}
        for key in dict.fromkeys(ids):
            spans = re.split(r'\[(?:separate span|relevant source windows|excerpt omitted)\]', records[key]['excerpt'])
            report['support'].extend({'id': key, 'quote': span.strip()} for span in spans if len(span.strip()) >= 3)
    except (ValueError, TypeError, KeyError):
        report['support'] = []
    return report


def direct_evidence(evidence):
    """Research may use search leads; verification receives observed content only."""
    try:
        return '\n'.join(json.dumps(row, ensure_ascii=False) for row in map(json.loads, evidence.splitlines())
                         if row.get('kind') in {'observation', 'task_input'})
    except (ValueError, TypeError):
        return ''


def relevant_excerpt(value, focus, limit):
    """Rank literal source windows, never synthesize evidence or splice quotations."""
    # Counting requires collection coverage, not isolated keyword hits. Preserve
    # a bounded, explicitly delimited matching section when the source exposes it.
    question = focus[0] if focus else ''
    headings = list(re.finditer(r'(?m)^([^\n]{1,100})\n\[\nedit\n\]', value))
    period = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:19|20)\d{2}\b', question, re.IGNORECASE)
    if period:
        for current, following in zip(headings, headings[1:]):
            if period[0].casefold() in current[1].casefold():
                section = value[current.start():following.start()]
                if len(section) <= 4000:
                    return value[:200] + '\n[relevant source windows]\n' + section, 3000
    count = re.search(r'\bhow many\s+(.{1,80}?)\s+(?:were|was|are|have|has|did|does|do|had|will|can)\b', question, re.IGNORECASE)
    if count:
        subject = re.sub(r'^the\s+', '', count[1], flags=re.IGNORECASE).casefold()
        for current, following in zip(headings, headings[1:]):
            if current[1].strip().casefold() == subject:
                section = value[current.start():following.start()]
                if len(section) <= 4000:
                    return value[:200] + '\n[relevant source windows]\n' + section, 2000
    stop={'what','which','where','when','that','this','with','from','their','about','under',
          'have','only','give','answer','number','find','were','does','they','into','mentioned'}
    terms={t.casefold() for text in focus for t in re.findall(r'[\w-]{4,}',text) if t.casefold() not in stop}
    phrases=[text.strip() for text in focus[1:] if 3<=len(text.strip())<=150]
    hits=[]
    for term in terms:
        hits.extend(m.start() for m in list(re.finditer(re.escape(term),value,re.IGNORECASE))[:20])
    for phrase in phrases:
        hits.extend(m.start() for m in list(re.finditer(re.escape(phrase),value,re.IGNORECASE))[:20])
    ranked=[]
    for pos in sorted(set(hits)):
        start=max(0,pos-200); end=min(len(value),pos+500); text=value[start:end]; lower=text.casefold()
        # Answer-bearing spans must not lose to keyword-dense menus/copyright.
        score=sum(term in lower for term in terms)+100*sum(p.casefold() in lower for p in phrases)
        ranked.append((score,start,end))
    windows=[];used=0
    for score,start,end in sorted(ranked,reverse=True):
        if any(start<b and end>a for a,b in windows):continue
        remaining=limit-260-used
        if remaining<180:break
        end=min(end,start+remaining);windows.append((start,end));used+=end-start+24
    if not windows:return value if len(value)<=limit else value[:limit-600]+'\n[excerpt omitted]\n'+value[-600:],0
    windows=with_table_headers(value,windows)
    header=value[:200]
    return header+'\n[relevant source windows]\n'+'\n[separate span]\n'.join(value[a:b] for a,b in sorted(windows)),max(s for s,_,_ in ranked)


def with_table_headers(value, windows):
    """A row far below its table header loses column meaning; add the literal header line as its own span."""
    extra=[]
    for start,_ in windows:
        opening=value.rfind('\n[TABLE ',0,start+1)
        if opening<0:continue
        closing=value.find('\n[END TABLE ',opening)
        if closing!=-1 and closing<start:continue
        line_start=value.find('\n',opening+1)+1
        line_end=value.find('\n',line_start)
        if line_start<=0 or line_end<0 or line_end-line_start>400 or not value.startswith('|',line_start):continue
        if any(a<=line_start<b for a,b in windows+extra):continue
        extra.append((line_start,line_end))
    return sorted(set(windows+extra))


def evidence_packet(events, start_index=0, budget=8000, focus=()):
    # Recent direct observations precede search snippets; never promote worker prose
    # or failed tool output into factual support.
    candidates = [(i, e) for i, e in enumerate(events)
                  if e.get('type') == 'input_evidence' or (i >= start_index
                  and e.get('type') == 'tool_call' and e.get('succeeded'))]
    prepared={}
    for i,event in candidates:
        value=str(event.get('result','')).split('\nNAVIGATION LINKS',1)[0].split('\n\nHARNESS SOURCE CHECK',1)[0].split('\nHARNESS PROGRESS',1)[0]
        limit=4000 if event.get('type')=='input_evidence' else 1800 if focus else 1400
        if focus and event.get('type')!='input_evidence' and event.get('name')!='search_web':
            prepared[i]=relevant_excerpt(value,focus,limit)
        else:
            prepared[i]=(value if len(value)<=limit else value[:limit-600]+'\n[excerpt omitted]\n'+value[-600:],0)
    candidates.sort(key=lambda x: (x[1].get('type') == 'input_evidence',
                                   x[1].get('name') != 'search_web', prepared[x[0]][1],x[0]), reverse=True)
    selected, seen = [], set()
    for i, event in candidates:
        value = str(event.get('result', ''))
        if not value or value in seen:
            continue
        if value.startswith('(completed with no output'):
            continue
        seen.add(value)
        excerpt = prepared[i][0]
        item = json.dumps({'id': f'E{i}', 'tool': event.get('name'),
                           'arguments': str(event.get('arguments', event.get('args', {})))[:300],
                           'kind': ('task_input' if event.get('type') == 'input_evidence' else
                                    'discovery_only' if event.get('name') == 'search_web' else 'observation'),
                           'excerpt': excerpt}, ensure_ascii=False)
        if sum(map(len, selected)) + len(item) + 1 <= budget:
            selected.append(item)
    return '\n'.join(selected)


def has_valid_support(raw, evidence):
    """Reject invented citations. This checks provenance, not factual entailment."""
    try:
        result = read_json_object(raw)
        records = {e['id']: e for e in map(json.loads, evidence.splitlines())}
        supports = result.get('support', [])
        return bool(supports) and all(
            isinstance(s, dict) and s.get('id') in records
            and records[s['id']]['kind'] in {'observation', 'task_input'}
            and len(s.get('quote', '').strip()) >= 3
            and any(_canonical_space(s['quote']) in _canonical_space(span)
                    for span in re.split(r'\[(?:separate span|relevant source windows|excerpt omitted)\]',records[s['id']]['excerpt']))
            for s in supports)
    except (ValueError, TypeError, KeyError):
        return False
