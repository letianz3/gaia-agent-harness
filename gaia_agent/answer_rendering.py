"""Conservative output-only formatting; never fed back into agent reasoning."""
import re


def render_final_answer(question, answer):
    return render_given_name(question, render_quantity(question, render_count(question, answer)))


def render_given_name(question, answer):
    """A request for "the first name" takes one given name.

    Space-separated given names ("Claus Peter") are reduced to the first; a
    hyphenated compound is one name and stays intact. Requests for several
    names, full names or surnames are left alone, as are non-name answers.
    """
    q=question.casefold()
    if not re.search(r'\bfirst name\b',q) or re.search(r'first names|full name|first and last|given names',q):
        return answer
    words=answer.strip().split()
    if not 2<=len(words)<=3 or not all(re.fullmatch(r"[^\W\d_]+(?:-[^\W\d_]+)*",w) and w[0].isupper() for w in words):
        return answer
    return words[0]


def render_count(question, answer):
    """Render a unique explicit quantity of the exact requested kind.

    Do not pick the first number: it may be a year or a different statistic.
    Ambiguity, uncertainty, missing units and negation preserve the original.
    """
    request=re.search(r'\bhow many\s+(.{1,80}?)\s+(?:were|was|are|have|has|did|does|do|had|will|can)\b',question,re.IGNORECASE)
    if not request or re.search(r"\b(?:not|no|unable|uncertain|guess|cannot|approximately|roughly|about|between|at least|at most)\b",answer,re.IGNORECASE):
        return answer
    unit=re.sub(r'^the\s+','',request[1],flags=re.IGNORECASE).strip()
    pattern=r'[\s-]+'.join(re.escape(word) for word in re.split(r'[\s-]+',unit))
    values=set(re.findall(r'(?<![\w.,-])(\d+(?:,\d{3})*(?:\.\d+)?)\s+'+pattern+r'\b',answer,re.IGNORECASE))
    return next(iter(values)) if len(values)==1 else answer


QUANTITY_REQUEST=re.compile(r'\b(?:how many|(?:the\s+)?(?:highest|lowest|largest|smallest|maximum|minimum|total|greatest)?\s*(?:number|count) of)\b',re.IGNORECASE)


def render_quantity(question, answer):
    """A quantity question takes a bare number; units echoed from the question are not the value.

    Only a single number followed by words that ALL occur in the question is
    reduced, so new information (another unit, a qualifier) is never dropped.
    """
    if not QUANTITY_REQUEST.search(question):
        return answer
    match=re.fullmatch(r'\s*(\d+(?:,\d{3})*(?:\.\d+)?)\s+([A-Za-z][A-Za-z\s-]{0,60}?)\s*\.?\s*',answer)
    if not match:
        return answer
    asked={w.casefold() for w in re.findall(r'[A-Za-z]+',question)}
    words=[w.casefold() for w in re.findall(r'[A-Za-z]+',match[2])]
    def echoed(word):
        return word in asked or word.rstrip('s') in asked or word+'s' in asked or word+'es' in asked
    return match[1] if words and all(echoed(w) for w in words) else answer
