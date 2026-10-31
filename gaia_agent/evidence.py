"""Bounded raw evidence for synthesis and independent verification."""
import json
import re


def read_json_object(raw):
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw.strip(), flags=re.I)
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def relevant_excerpt(value, focus, limit):
    """Rank literal source windows, never synthesize evidence or splice quotations."""
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
    header=value[:200]
    return header+'\n[relevant source windows]\n'+'\n[separate span]\n'.join(value[a:b] for a,b in sorted(windows)),max(s for s,_,_ in ranked)


def evidence_packet(events, start_index=0, budget=8000, focus=()):
    # Recent direct observations precede search snippets; never promote worker prose
    # or failed tool output into factual support.
    candidates = [(i, e) for i, e in enumerate(events)
                  if e.get('type') == 'input_evidence' or (i >= start_index
                  and e.get('type') == 'tool_call' and e.get('succeeded'))]
    prepared={}
    for i,event in candidates:
        value=str(event.get('result','')).split('\nNAVIGATION LINKS',1)[0]
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
            and any(' '.join(s['quote'].split()) in ' '.join(span.split())
                    for span in re.split(r'\[(?:separate span|relevant source windows|excerpt omitted)\]',records[s['id']]['excerpt']))
            for s in supports)
    except (ValueError, TypeError, KeyError):
        return False
