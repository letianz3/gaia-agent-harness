import json

from gaia_agent.evidence import evidence_packet, has_valid_support
from gaia_agent.verification import select_verified


def test_recovery_deduplicates_successful_reads_but_allows_new_queries_and_retries():
    from types import SimpleNamespace

    from gaia_agent.verification import RecoveryRegistry
    calls=[]
    def execute(name,args):
        calls.append((name,args))
        return 'new source', True
    trace=SimpleNamespace(events=[
        {'name': 'fetch_url','arguments': '{"url":"https://example.org/a"}','succeeded': True,'result': 'old source'},
        {'name': 'fetch_url','arguments': '{"url":"https://example.org/b"}','succeeded': False,'result': 'timeout'}])
    proxy=RecoveryRegistry(SimpleNamespace(execute=execute),trace,'source question')
    value,ok=proxy.execute('fetch_url','{ "url": "https://example.org/a" }')
    assert ok and 'ALREADY OBSERVED' in value and not calls
    proxy.execute('fetch_url','{"url":"https://example.org/b"}')
    proxy.execute('search_web','{"query":"new query"}')
    assert len(calls)==2


def observation(text):return {'type': 'tool_call','name': 'fetch_url','succeeded': True,'result': text}


def test_middle_passage_survives_focused_packet_and_noise():
    body='SOURCE: https://example.org/paper\n'+'irrelevant '*2000+'\nResearcher ABC was funded by award ZX-8912.\n'+'tail '*3000
    events=[observation(body)]+[observation('generic unrelated page '+str(i)) for i in range(15)]
    p=evidence_packet(events,focus=('Which award supported researcher ABC?','ZX-8912','WRONG-77'))
    assert len(p)<=8000 and 'Researcher ABC was funded by award ZX-8912.' in p
    assert has_valid_support(json.dumps({'support':[{'id':'E0','quote':'Researcher ABC was funded by award ZX-8912.'}]}),p)


def test_both_candidates_receive_relevant_evidence():
    events=[observation('SOURCE: https://example.org/a\n'+'x '*5000+'Candidate ALPHA belongs to the wrong researcher.'),
            observation('SOURCE: https://example.org/b\n'+'y '*5000+'Candidate BETA belongs to researcher ABC.')]
    p=evidence_packet(events,focus=('Which candidate belongs to researcher ABC?','ALPHA','BETA'))
    assert 'ALPHA belongs' in p and 'BETA belongs' in p


def test_metadata_keyword_density_cannot_evict_answer_passage():
    question='What surname appears in chemistry exercises licensed by Alice Baker and Carol Davis in introductory materials?'
    body=(question+' copyright licensed metadata ')*60+'\nThe horse doctor was called Exampleton.\n'+(question+' footer ')*60
    packet=evidence_packet([observation(body)],focus=(question,'Exampleton','Anothername'))
    assert 'horse doctor was called Exampleton' in packet


def test_provenance_allows_layout_whitespace_not_paraphrase_or_joined_spans():
    p=json.dumps({'id': 'E0','kind': 'observation','excerpt': 'award\n ZX-8912 [separate span] unrelated'})
    def check(q):return has_valid_support(json.dumps({'support':[{'id':'E0','quote':q}]}),p)
    assert check('award ZX-8912')
    assert not check('grant ZX-8912')
    assert not check('ZX-8912 [separate span] unrelated')


def test_no_incumbent_privilege_and_no_unsupported_pass():
    p=json.dumps({'id': 'E0','kind': 'observation','excerpt': 'Researcher ABC received award ZX-8912.'})
    supported={'verdict':'PASS','support':[{'id':'E0','quote':'ABC received award ZX-8912'}]}
    uncertain={'verdict':'UNCERTAIN','support':[]}
    assert select_verified({'candidates':[dict(supported,id='A'),dict(uncertain,id='B')]},p)=='A'
    assert select_verified({'candidates':[dict(uncertain,id='A'),dict(supported,id='B')]},p)=='B'
    assert select_verified({'candidates':[dict(uncertain,id='A'),dict(uncertain,id='B')]},p) is None
    assert select_verified({'candidates':[dict(supported,id='A'),dict(supported,id='B')]},p) is None
    assert select_verified({'candidates':[dict(uncertain,id='A'),{'id': 'B','verdict': 'PASS','support': []}]},p) is None


def test_navigation_is_bounded_and_not_factual_support():
    from gaia_agent.tracing import Trace
    from gaia_agent.verification import navigation_evidence
    trace=Trace('test','Which chapter mentions velocity?')
    for i in range(4):trace.add('tool_call',name='fetch_url',succeeded=True,result=f'SOURCE: https://example.org/{i}\nvelocity chapter')
    class Registry:
        calls=0
        def execute(self,name,args):
            self.calls+=1
            return 'SOURCE: https://example.org/parent\nBook index\nNAVIGATION LINKS (discovery only, not factual evidence):\n'+json.dumps([['Answer SECRET','https://example.org/chapter']]*20),True
    registry=Registry();notes=json.loads(navigation_evidence(registry,trace,trace.question))
    assert registry.calls==2 and len(notes)==2 and len(notes[0]['links'])==12
    assert 'SECRET' not in evidence_packet(trace.events,focus=(trace.question,'SECRET'))
