"""Bounded source exploration, independent of benchmark questions and answers."""
import hashlib
import json
import re
import threading
from urllib.parse import unquote, urlsplit, urlunsplit


def explicit_authors(question):
    """Extract only explicitly named authors; absence is not a contradiction."""
    match = re.search(
        r'\b(?:licensed|authored|written|edited)\s+by\s+(.+?)(?=\s+under\b|[?;\n]|$)',
        question, re.IGNORECASE,
    )
    if not match or len(match[1]) > 100:
        return []
    names = re.split(r'\s*(?:&|\band\b)\s*', match[1])
    return [name for name in names if re.fullmatch(r"[A-Z][\w'-]+(?:\s+[A-Z][\w'-]+){1,3}", name)]


def source_key(url):
    parts = urlsplit(url)
    # Preserve query strings: they may identify distinct documents.
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), unquote(parts.path), parts.query, ''))


class SourceProgressRegistry:
    """Allow one body read and one navigation refinement per source per task.

    Successful observations seed the ledger across worker and repair loops.
    Failures do not consume the source allowance. Other tools are unaffected.
    """
    def __init__(self, registry, trace):
        self.registry, self.trace = registry, trace
        self.authors = explicit_authors(trace.question)
        self.visits = {}
        self.bodies = {}
        self.texts = {}
        self.lock = threading.RLock()
        self.source_locks = {}
        for event in trace.events:
            if event.get('name') == 'fetch_url' and event.get('succeeded'):
                try:
                    url = json.loads(event.get('arguments', '{}')).get('url')
                except (ValueError, TypeError):
                    continue
                if url and event.get('result', '').startswith('SOURCE: '):
                    key = source_key(url)
                    self.visits[key] = self.visits.get(key, 0) + 1
                    self.texts[key] = event['result']

    def __getattr__(self, name):
        return getattr(self.registry, name)

    def cached_passages(self, key, query, budget=12000):
        """Complete rendered tables when they fit, else literal windows for the query."""
        raw = self.texts.get(key)
        if not raw:
            return ''
        body = raw.split('\nNAVIGATION LINKS', 1)[0]
        from .web_tables import parse_table_blocks
        blocks = [block for block in parse_table_blocks(body) if block['complete']]
        text = '\n'.join('\n'.join([f"[TABLE {b['table']}]", *b['lines'], f"[END TABLE {b['table']}]"])
                         for b in blocks)
        if blocks and len(text) <= budget:
            title = body.split('\n', 2)[1][:200] if '\n' in body else ''
            return title + '\n' + text
        from .evidence import relevant_excerpt
        return relevant_excerpt(body, (self.trace.question, query), 4000)[0]

    def execute(self, name, arguments):
        if name != 'fetch_url':
            return self.registry.execute(name, arguments)
        try:
            args = json.loads(arguments)
            key = source_key(args['url'])
        except (ValueError, TypeError, KeyError):
            return self.registry.execute(name, arguments)
        # Serialize variants of the SAME source without blocking independent reads.
        with self.lock:
            gate = self.source_locks.setdefault(key, threading.RLock())
        with gate:
            if self.visits.get(key, 0) >= 2:
                self.trace.add('source_progress', url=key, action='switch_source')
                limit = ('SOURCE EXPLORATION LIMIT: this document has already been read and '
                         'navigation explored. Changing link_query only filters links; it does not '
                         'search the body or locate another book.')
                cached = self.cached_passages(key, args.get('link_query') or '')
                if cached:
                    # A valid source stays usable: refusing it outright made repair
                    # loops answer from memory or abandon the right document.
                    # Not a new observation (ok=False): the original read is already evidence.
                    return (limit + ' Its stored text is repeated below; use it. Only if it lacks '
                            'the fact, open a DIFFERENT observed URL.\n'
                            'CACHED SOURCE TEXT (literal, not a new fetch):\n' + cached), False
                return (limit + ' Search for the requested source '
                        'identity, then open a DIFFERENT observed URL. Suggested identity query: '
                        + ' '.join(json.dumps(author) for author in self.authors)), False
            raw, ok = self.registry.execute(name, arguments)
            if not ok or not raw.startswith('SOURCE: '):
                return raw, ok
            self.visits[key] = self.visits.get(key, 0) + 1
            self.texts[key] = raw
            body = raw.split('\nNAVIGATION LINKS', 1)[0]
            fingerprint = hashlib.sha256(body.encode()).hexdigest()
            unchanged = self.bodies.get(key) == fingerprint
            self.bodies[key] = fingerprint
            normalized = ' '.join(body.casefold().split())
            missing = [author for author in self.authors if author.casefold() not in normalized]
            notes = ''
            if missing:
                self.trace.add('source_identity', url=key, status='unconfirmed', missing=missing)
                notes += ('\n\nHARNESS SOURCE CHECK (not source evidence): Requested author identity '
                        'is not confirmed on this page. This is not proof of mismatch, but a matching '
                        'chapter title alone is insufficient. Locate the book/parent page and '
                        'verify its author before using this chapter as the requested source. '
                        'Try search_web with: ' + ' '.join(json.dumps(author) for author in self.authors))
            if unchanged:
                notes += '\nHARNESS PROGRESS: body unchanged; navigation links are discovery only.'
            body, marker, links = raw.partition('\nNAVIGATION LINKS')
            raw = body + notes + marker + links
            return raw, ok
