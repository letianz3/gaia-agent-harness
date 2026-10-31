"""Conservative output-only formatting; never fed back into agent reasoning."""
import re


def render_final_answer(question, answer):
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
